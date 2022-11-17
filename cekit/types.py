from typing import Any, Dict, List, TypeVar, Union

_T = TypeVar("_T")

# TODO: Once we drop support for 3.9, we should change these to TypeAliases, PEP613

ContentSetType = Dict[str, List[str]]

DependencyDefinition = Dict[str, Dict[str, Union[str, dict]]]

# Name to clarify when we use strings as paths.
PathType = str

RawDescriptor = Dict[str, Any]
