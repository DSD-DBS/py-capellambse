// SPDX-FileCopyrightText: Copyright DB InfraGO AG
// SPDX-License-Identifier: Apache-2.0

use std::{
    borrow::Cow,
    cmp::Ordering,
    collections::{HashMap, HashSet},
    sync::LazyLock,
};

use pyo3::{
    exceptions::{PyTypeError, PyValueError},
    intern,
    prelude::*,
    types::{PyDict, PyString, PyType},
};

const MEM_BUFFER_SIZE: usize = 2 * 1024 * 1024; // 2 MiB

#[cfg(not(windows))]
const LINESEP: &[u8; 1] = b"\n";
#[cfg(windows)]
const LINESEP: &[u8; 2] = b"\r\n";

const INDENT_WIDTH: usize = 2;
const INDENT_CHAR: u8 = ' ' as u8;

static ALWAYS_EXPANDED_TAGS: LazyLock<HashSet<(Option<&Cow<'static, str>>, &'static str)>> =
    LazyLock::new(|| [(None, "bodies"), (None, "semanticResources")].into());
static EARLY_NAMESPACES: LazyLock<HashSet<&'static str>> = LazyLock::new(|| {
    [
        "http://www.omg.org/XMI",
        "http://www.w3.org/2001/XMLSchema-instance",
    ]
    .into()
});

#[pyfunction]
#[pyo3(signature=(tree, /, *, line_length, siblings, file))]
pub fn serialize<'py>(
    py: Python<'py>,
    tree: &'py Bound<PyAny>,
    line_length: usize,
    siblings: bool,
    file: Option<Bound<PyAny>>,
) -> PyResult<Option<Vec<u8>>> {
    Ok(Serializer::new(py, line_length, file)?
        .feed_tree(tree, siblings)?
        .finish()?)
}

struct Serializer<'py> {
    buf: Vec<u8>,
    pos: usize,
    line_length: usize,
    write: Option<Bound<'py, PyAny>>,

    etree_element: Bound<'py, PyType>,
    etree_comment: Bound<'py, PyType>,
}

impl<'py> Serializer<'py> {
    fn new(
        py: Python<'py>,
        line_length: usize,
        output: Option<Bound<'py, PyAny>>,
    ) -> PyResult<Self> {
        let etree = py.import("lxml.etree").expect("cannot import lxml.etree");
        let etree_element = etree
            .getattr("_Element")
            .expect("lxml.etree does not have _Element")
            .downcast::<PyType>()
            .expect("lxml.etree._Element is not a type")
            .clone();
        let etree_comment = etree
            .getattr("_Comment")
            .expect("lxml.etree does not have _Comment")
            .downcast::<PyType>()
            .expect("lxml.etree._Comment is not a type")
            .clone();

        let write = match output {
            Some(output) => Some(output.getattr(intern!(py, "write"))?),
            None => None,
        };

        Ok(Self {
            buf: Vec::with_capacity(MEM_BUFFER_SIZE),
            pos: 0,
            line_length,
            write,

            etree_element,
            etree_comment,
        })
    }

    fn feed_tree(mut self, tree: &Bound<PyAny>, siblings: bool) -> PyResult<Self> {
        let py = tree.py();

        if !tree.is_instance(&self.etree_element)? {
            Err(PyTypeError::new_err(format!(
                "Unserializable object type {}, expected lxml.etree._Element",
                tree.get_type()
                    .name()
                    .map(|n| n.extract::<String>().expect("__name__ is not valid UTF-8"))
                    .unwrap_or_else(|_| "<unknown type>".into())
            )))?;
        }

        fn check_has_no_tail(e: &Bound<PyAny>) -> PyResult<()> {
            if e.getattr(intern!(e.py(), "tail"))
                .expect("element/comment has no tail attribute")
                .is_truthy()?
            {
                Err(PyValueError::new_err(
                    "Text content outside of the main tree, try 'siblings=False'",
                ))?
            }
            Ok(())
        }

        if siblings {
            let kwargs = PyDict::new(py);
            kwargs
                .set_item(intern!(py, "preceding"), true)
                .expect("cannot create method kwargs");
            let preceding_siblings = tree
                .call_method(intern!(py, "itersiblings"), (), Some(&kwargs))?
                .try_iter()
                .expect("itersiblings did not return an iterable")
                .collect::<PyResult<Vec<_>>>()?;
            drop(kwargs);

            for i in preceding_siblings.iter().rev() {
                if !i.is_instance(&self.etree_comment)? {
                    Err(PyValueError::new_err(
                        "Non-comment before main tree, try 'siblings=False'",
                    ))?
                }

                check_has_no_tail(i)?;
                self.eat_comment(i, 0)?;
                self.emit_linebreak(0)?;
            }

            check_has_no_tail(tree)?;
        }

        self.eat_element(tree, 0, &HashMap::default())?;

        if siblings {
            for i in tree
                .call_method0(intern!(py, "itersiblings"))?
                .try_iter()
                .expect("itersiblings did not return an iterable")
            {
                let i = &i?;
                if !i.is_instance(&self.etree_comment)? {
                    Err(PyValueError::new_err(
                        "Non-comment after main tree, try 'siblings=False'",
                    ))?
                }

                check_has_no_tail(i)?;
                self.eat_comment(i, 0)?;
                self.emit_linebreak(0)?;
            }
        }

        Ok(self)
    }

    fn finish(mut self) -> PyResult<Option<Vec<u8>>> {
        self.emit_linebreak(0)?;
        if let Some(write) = self.write {
            write.call1((self.buf,))?;
            Ok(None)
        } else {
            Ok(Some(self.buf))
        }
    }
}

impl<'py> Serializer<'py> {
    fn eat_comment(&mut self, element: &Bound<PyAny>, indent: usize) -> PyResult<()> {
        let py = element.py();
        let text = element
            .getattr(intern!(py, "text"))
            .expect("comment has no text");
        let text = text
            .downcast::<PyString>()
            .expect("comment text is not a string or none")
            .to_cow()
            .expect("comment text is not valid UTF-8");

        self.emit_linebreak(indent)?;
        self.emit_raw_string(b"<!--")?;
        self.digest_multiline_text(&text, EscapeCharset::Comment)?;
        self.emit_raw_string(b"-->")?;
        Ok(())
    }

    fn eat_element(
        &mut self,
        e: &Bound<PyAny>,
        indent: usize,
        parent_nsmap: &HashMap<Cow<'_, str>, Cow<'_, str>>,
    ) -> PyResult<()> {
        let py = e.py();
        assert!(e.is_instance(&self.etree_element).unwrap_or(false));

        let mut nsmap_alias2uri = e
            .getattr("nsmap")
            .expect("element has no nsmap")
            .downcast::<PyDict>()
            .expect("nsmap is not a dict")
            .iter()
            .map(|(k, v)| {
                (
                    k.downcast().expect("nsmap alias is not a string").clone(),
                    v.downcast().expect("nsmap uri is not a string").clone(),
                )
            })
            .collect::<Vec<(Bound<PyString>, Bound<PyString>)>>();
        nsmap_alias2uri.sort_unstable_by(namespaces_sort);
        let nsmap_uri2alias = nsmap_alias2uri
            .iter()
            .map(|(k, v)| (v.to_string_lossy(), k.to_string_lossy()))
            .collect::<HashMap<Cow<'_, str>, Cow<'_, str>>>();

        self.emit_raw_string(b"<")?;
        let unresolved_tag = self.unresolve_namespace(e, &nsmap_uri2alias);
        let unresolved_tag = (unresolved_tag.0.as_ref(), unresolved_tag.1.as_str());
        self.digest_namespaced_name(unresolved_tag)?;

        let attribs = PyDict::new(py);
        attribs
            .call_method1(
                intern!(py, "update"),
                (e.getattr(intern!(py, "attrib"))
                    .expect("cannot get attributes of element"),),
            )
            .expect("cannot copy element attributes");

        for attr in [
            intern!(py, "{http://www.omg.org/XMI}version"),
            intern!(py, "{http://www.omg.org/XMI}type"),
            intern!(py, "{http://www.omg.org/XMI}id"),
            intern!(py, "{http://www.w3.org/2001/XMLSchema-instance}type"),
        ] {
            let value = attribs
                .call_method1(intern!(py, "pop"), (attr, py.None()))
                .expect("cannot pop from attrib dict");
            if !value.is_none() {
                let value = value
                    .downcast::<PyString>()
                    .expect("attrib value is not a string");
                let (ns, ln) = self.unresolve_namespace(attr, &nsmap_uri2alias);
                if self.pos > self.line_length {
                    self.emit_linebreak(indent + 2)?;
                } else {
                    self.emit_raw_string(b" ")?;
                }
                self.digest_attr_pair(
                    (ns.as_ref(), &ln),
                    &value.to_cow().expect("attrib value is not valid UTF-8") as &str,
                )?;
            }
        }

        for (alias, uri) in nsmap_alias2uri.iter() {
            if !parent_nsmap.contains_key(&uri.to_cow()? as &str) {
                if self.pos > self.line_length {
                    self.emit_linebreak(indent + 2)?;
                } else {
                    self.emit_raw_string(b" ")?;
                }
                self.digest_attr_pair(
                    (Some(&Cow::Borrowed("xmlns")), &alias.to_cow()? as &str),
                    &uri.to_cow()? as &str,
                )?;
            }
        }

        let has_parent = !e
            .call_method0(intern!(py, "getparent"))
            .map(|o| !o.is_none())
            .unwrap_or(false);
        let mut force_break = false;
        for kv in attribs.items().iter() {
            let (key, value) = kv
                .extract::<(Bound<PyString>, Bound<PyString>)>()
                .expect("attrib key/value is not a string 2-tuple");
            let (ns, key) = self.unresolve_namespace(&key, &nsmap_uri2alias);
            if force_break || self.pos > self.line_length {
                self.emit_linebreak(indent + 2)?;
            } else {
                self.emit_raw_string(b" ")?;
            }
            self.digest_attr_pair(
                (ns.as_ref(), &key),
                &value.to_cow().expect("attrib value is not valid UTF-8"),
            )?;

            force_break = has_parent && ns.is_none() && key == "id";
        }

        let text = e.getattr(intern!(py, "text")).expect("element has no text");
        let has_children = e.len().expect("cannot get len() of element") > 0;
        if text.is_none() && !has_children && !ALWAYS_EXPANDED_TAGS.contains(&unresolved_tag) {
            self.emit_raw_string(b"/>")?;
            return Ok(());
        }
        self.emit_raw_string(b">")?;

        let mut trailing_text = if !text.is_none() {
            let text = text
                .downcast::<PyString>()
                .expect("element text is not a string");
            self.digest_multiline_text(
                &text.to_cow().expect("element text is not valid UTF-8"),
                EscapeCharset::Text,
            )?;
            true
        } else {
            false
        };
        for child in e.try_iter().expect("cannot iterate over element") {
            if !trailing_text {
                self.emit_linebreak(indent + 1)?;
            }

            let child = child.expect("cannot iterate over element");
            if child.is_instance(&self.etree_comment).unwrap_or(false) {
                self.eat_comment(&child, indent + 1)?;
            } else if child.is_instance(&self.etree_element).unwrap_or(false) {
                self.eat_element(&child, indent + 1, &nsmap_uri2alias)?;
            } else {
                Err(PyTypeError::new_err(format!(
                    "expected only _Element and _Comment in tree, found {}",
                    child
                        .get_type()
                        .name()
                        .and_then(|n| n.extract::<String>())
                        .unwrap_or_else(|_| "<unknown type>".into())
                )))?
            }

            let tail = child
                .getattr(intern!(py, "tail"))
                .expect("element has no tail attribute");
            trailing_text = if !tail.is_none() {
                let tail = tail
                    .downcast::<PyString>()
                    .expect("element tail is not a string");
                self.digest_multiline_text(
                    &tail.to_cow().expect("element tail is not valid UTF-8"),
                    EscapeCharset::Text,
                )?;
                true
            } else {
                false
            }
        }

        if has_children && !trailing_text {
            self.emit_linebreak(indent)?;
        }

        self.emit_raw_string(b"</")?;
        self.digest_namespaced_name(unresolved_tag)?;
        self.emit_raw_string(b">")?;

        py.check_signals()
    }
}

impl<'py> Serializer<'py> {
    fn unresolve_namespace<'n>(
        &self,
        e: &Bound<PyAny>,
        nsmap: &'n HashMap<Cow<'n, str>, Cow<'n, str>>,
    ) -> (Option<Cow<'n, str>>, String) {
        let py = e.py();
        let tag = if let Ok(tag) = e.downcast::<PyString>() {
            tag.clone()
        } else if e.is_instance(&self.etree_element).unwrap_or(false) {
            e.getattr(intern!(py, "tag"))
                .expect("element has no tag")
                .downcast::<PyString>()
                .expect("tag is not a string")
                .clone()
        } else {
            panic!(
                "cannot unresolve namespace on a {}",
                e.get_type()
                    .name()
                    .and_then(|n| n.extract::<String>())
                    .unwrap_or_else(|_| "<unknown type>".into())
            );
        };
        let tag = tag.to_cow().expect("namespaced name is not valid UTF-8");
        assert!(tag.len() > 0, "empty tag");

        if tag.chars().nth(0) == Some('{') {
            let closing = tag.find("}").expect("malformed tag (no '}')");
            let uri = &tag[1..closing];
            assert!(uri.len() > 0, "unnamed namespace is not supported");
            let ns = nsmap.get(uri).expect("namespace not in nsmap").clone();
            (Some(ns), tag[closing + 1..].to_string())
        } else {
            (None, tag.to_string())
        }
    }

    fn digest_string(&mut self, string: &str, charset: EscapeCharset) -> PyResult<()> {
        let string = escape(string, charset);
        self.emit_raw_string(string.as_bytes())
    }

    fn digest_multiline_text(&mut self, text: &str, charset: EscapeCharset) -> PyResult<()> {
        for (i, line) in text.split('\n').enumerate() {
            if i > 0 {
                self.emit_linebreak(0)?;
            }
            self.digest_string(line, charset)?;
        }

        Ok(())
    }

    fn digest_namespaced_name(&mut self, name: (Option<&Cow<'_, str>>, &str)) -> PyResult<()> {
        if let Some(ns) = name.0 {
            self.emit_raw_string(ns.as_bytes())?;
            self.emit_raw_string(b":")?;
        }
        self.emit_raw_string(name.1.as_bytes())
    }

    fn digest_attr_pair(
        &mut self,
        key: (Option<&Cow<'_, str>>, &str),
        value: &str,
    ) -> PyResult<()> {
        self.digest_namespaced_name(key)?;
        self.emit_raw_string(b"=\"")?;
        self.digest_string(&value, EscapeCharset::Attribute)?;
        self.emit_raw_string(b"\"")
    }
}

impl<'py> Serializer<'py> {
    fn emit_linebreak(&mut self, indent: usize) -> PyResult<()> {
        if let Some(ref write) = self.write {
            let needed_space = LINESEP.len() + INDENT_WIDTH * indent;
            assert!(needed_space < MEM_BUFFER_SIZE);
            if self.buf.len() + needed_space > MEM_BUFFER_SIZE {
                write.call1((&self.buf,))?;
                self.buf.clear();
            }
        }

        self.buf.extend(LINESEP);
        (0..INDENT_WIDTH * indent).for_each(|_| self.buf.push(INDENT_CHAR));
        self.pos = INDENT_WIDTH * indent;

        Ok(())
    }

    fn emit_raw_string(&mut self, string: &[u8]) -> PyResult<()> {
        if let Some(ref write) = self.write {
            let mut idx = 0;
            loop {
                let space = MEM_BUFFER_SIZE - self.buf.len();
                self.buf.extend(string.iter().skip(idx).take(space));
                idx += space;
                if MEM_BUFFER_SIZE - self.buf.len() == 0 {
                    write.call1((&self.buf,))?;
                    self.buf.clear();
                }
                if idx >= string.len() {
                    break;
                }
            }
        } else {
            self.buf.extend(string);
        }
        self.pos += string.len();

        Ok(())
    }
}

#[derive(Clone, Copy, Debug)]
enum EscapeCharset {
    Attribute,
    Comment,
    Text,
}

fn escape<'a>(string: &'a str, charset: EscapeCharset) -> Cow<'a, str> {
    let mut output = None;
    for (i, c) in string.char_indices() {
        let escape = match (charset, c) {
            (_, '\x00'..='\x08' | '\x0A'..='\x1F' | '\x7F') => true,
            (EscapeCharset::Attribute, '\x09') => true,
            (EscapeCharset::Attribute | EscapeCharset::Text, '"' | '&' | '<') => true,
            (EscapeCharset::Comment, '>') => true,
            _ => false,
        };

        if escape {
            if output.is_none() {
                output = Some(string[..i].to_owned());
            }
            let escaped = match c {
                '&' => "&amp;",
                '<' => "&lt;",
                '>' => "&gt;",
                '"' => "&quot;",
                c => &format!("&#x{:X};", c as u64),
            };
            output.as_mut().unwrap().push_str(escaped);
        } else if let Some(ref mut o) = output {
            o.push(c);
        }
    }

    match output {
        Some(output) => Cow::Owned(output),
        None => Cow::Borrowed(string),
    }
}

fn namespaces_sort(
    left: &(Bound<PyString>, Bound<PyString>),
    right: &(Bound<PyString>, Bound<PyString>),
) -> Ordering {
    let left_early = EARLY_NAMESPACES.contains(&left.1.to_string_lossy() as &str);
    let right_early = EARLY_NAMESPACES.contains(&right.1.to_string_lossy() as &str);

    match (left_early, right_early) {
        (true, false) => Ordering::Less,
        (false, true) => Ordering::Greater,
        _ => left.0.to_string_lossy().cmp(&right.0.to_string_lossy()),
    }
}
