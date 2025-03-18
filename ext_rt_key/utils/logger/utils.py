"""
:mod:`utils` -- Вспомогательные утилиты
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

import yaml
import yaml.emitter
import yaml.representer
import yaml.resolver
import yaml.serializer

__all__ = ("PrettyDumper",)


class IndentingEmitter(yaml.emitter.Emitter):
    """https://stackoverflow.com/a/70423579"""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        """Ensure that lists items are always indented."""
        return super().increase_indent(
            flow=False,
            indentless=False,
        )


class PrettyDumper(
    IndentingEmitter,
    yaml.serializer.Serializer,
    yaml.representer.Representer,
    yaml.resolver.Resolver,
):
    """
    https://stackoverflow.com/a/70423579
    """

    def __init__(  # type: ignore
        self,
        stream,
        default_style=None,
        default_flow_style=False,
        canonical=None,
        indent=None,
        width=None,
        allow_unicode=None,
        line_break=None,
        encoding=None,
        explicit_start=None,
        explicit_end=None,
        version=None,
        tags=None,
        sort_keys=True,
    ):
        IndentingEmitter.__init__(
            self,
            stream,
            canonical=canonical,
            indent=indent,
            width=width,
            allow_unicode=allow_unicode,
            line_break=line_break,
        )
        yaml.serializer.Serializer.__init__(
            self,
            encoding=encoding,
            explicit_start=explicit_start,
            explicit_end=explicit_end,
            version=version,
            tags=tags,
        )
        yaml.representer.Representer.__init__(
            self,
            default_style=default_style,
            default_flow_style=default_flow_style,
            sort_keys=sort_keys,
        )
        yaml.resolver.Resolver.__init__(self)
