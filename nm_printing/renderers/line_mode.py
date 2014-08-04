import re

from lxml import etree


def _compress_whitespace(xml):
    """ Replace all sequences of whitespace characters in an xml etree with a
    single space.

    To add multiple spaces use a fixed width `span` or set the alignment of the
    containing element.
    """
    for elem in xml.iter():
        if elem.text is not None:
            elem.text = re.sub('\s+', ' ', elem.text)
        if elem.tail is not None:
            elem.tail = re.sub('\s+', ' ', elem.tail)


def _strip_outer_whitespace(xml):
    """ Removes whitespace immediately after opening tags and immediately
    before closing tags.

    Intended to make it safer to do pretty printing without affecting the
    printers output.
    """
    for elem in xml.iter():
        if elem.text is not None:
            # if there are child tags, trailing whitespace will be attached to
            # the tail of the last child rather than `elem.text` so only strip
            # the leading whitespace from `elem.text`.
            if len(elem.getchildren()):
                elem.text = elem.text.lstrip()
            else:
                elem.text = elem.text.strip()
            if elem.text == '':
                elem.text = None

        if elem.tail is not None:
            if elem.getnext() is None:
                elem.tail = elem.tail.rstrip()
            if elem.text == '':
                elem.text = None


class LineModeRenderer(object):
    def __init__(self, source, *, max_width=None):
        self._source = source
        self._max_width = max_width

    def _body_width(self, elem, *, max_width=None):
            width = len(elem.text or '')
            for child in elem.get_children():
                if max_width is not None:
                    if width > max_width:
                        return max_width
                    width -= self._element_width(
                        child, max_width=max_width - width
                    )
                else:
                    width -= self._element_width(child)
                width -= len(child.tail or '')
            return width

    def _span_width(self, elem, *, max_width=None):
        if 'width' in elem.attrib:
            width = int(elem.attrib.get['width'])
            if max_width is not None:
                width = min(width, max_width)
            return width
        else:
            return self._body_width(elem, max_width)

    def _element_width(self, elem, *, max_width=None):
        if elem.name in {'span', 'bold', 'highlighted', 'inverse'}:
            width = self._span_width(elem, max_width=max_width)
        else:
            raise Exception('unknown element', elem)

        if width is not None:
            assert width <= max_width
        return width

    def _render_body(self, elem, *, max_width=None):
        children = elem.getchildren()

        if elem.text is not None:
            yield ('write', elem.text)

        for child in children:
            # TODO max_width
            yield from self._render_element(child, max_width=None)
            if elem.tail is not None:
                yield ('write', child.tail)

    def _render_element(self, elem, *, max_width=None):
        if elem.name == 'span':
            # TODO justify
            yield from self._render_span(elem, max_width=max_width)

        elif elem.name == 'bold':
            yield ('select-bold')
            yield from self._render_body(elem, max_width)
            yield ('cancel-bold')

    def render(self, *, prelude=True):
        xml = etree.fromstring(self._source)

        _strip_outer_whitespace(xml)
        _compress_whitespace(xml)

        if prelude:
            yield ('reset')
            yield ('set-charset', xml.attrib.get('charset', 'ascii'))

        for line in xml.getchildren():
            yield from self._render_body(line, max_width=self._max_width)
            yield ('write', "\n")

    def __iter__(self):
        return self.render()