import importlib
import json

from docutils import nodes
from docutils.parsers.rst import directives

from sphinx.util.docutils import SphinxDirective
from sphinx.directives.code import container_wrapper


class SchemaDirective(SphinxDirective):
    has_content = True
    required_arguments = 1
    optional_arguments = 1

    option_spec = {
        'name': directives.unchanged
    }

    def run(self):
        module, clazz = self.arguments[0].rsplit(".", 1)

        module = importlib.import_module(module)
        clazz = getattr(module, clazz)

        if not clazz.SCHEMA:
            return []

        code = nodes.literal_block(text=json.dumps(clazz.SCHEMA, indent=4, sort_keys=True))
        code['language'] = 'json'

        code = container_wrapper(self, code, "Schema")

        self.add_name(code)

        return [code]


def setup(app):
    app.add_directive('schema', SchemaDirective,
                      content=0, arguments=(1, 0, 0),
                      linenos=directives.flag,
                      language=directives.unchanged,
                      encoding=directives.encoding)

    # TODO: Replace nodes after the source was changed
    # app.connect('source-read', process_schema_nodes)
    # app.connect('doctree-resolved', process_schema_nodes)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
