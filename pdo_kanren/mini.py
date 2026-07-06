"""A tiny miniKanren-style relational core.

This is intentionally small: enough logic-variable machinery to express the
PDO payload generator as relations without pulling in a Python package that may
not support the user's local Python version yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import count
from typing import Any, Callable, Generator, Iterable


State = dict["Var", Any]
Goal = Callable[[State], Iterable[State]]


@dataclass(frozen=True)
class Var:
    name: str
    index: int

    def __repr__(self) -> str:
        return f"~{self.name}{self.index}"


_counter = count()


def var(name: str = "q") -> Var:
    return Var(name, next(_counter))


def walk(term: Any, state: State) -> Any:
    while isinstance(term, Var) and term in state:
        term = state[term]
    return term


def unify(left: Any, right: Any, state: State) -> State | None:
    left = walk(left, state)
    right = walk(right, state)
    if left == right:
        return state
    if isinstance(left, Var):
        next_state = dict(state)
        next_state[left] = right
        return next_state
    if isinstance(right, Var):
        next_state = dict(state)
        next_state[right] = left
        return next_state
    if isinstance(left, tuple) and isinstance(right, tuple) and len(left) == len(right):
        next_state = state
        for l_item, r_item in zip(left, right):
            next_state = unify(l_item, r_item, next_state)
            if next_state is None:
                return None
        return next_state
    if isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        next_state = state
        for l_item, r_item in zip(left, right):
            next_state = unify(l_item, r_item, next_state)
            if next_state is None:
                return None
        return next_state
    if isinstance(left, dict) and isinstance(right, dict) and left.keys() == right.keys():
        next_state = state
        for key in left:
            next_state = unify(left[key], right[key], next_state)
            if next_state is None:
                return None
        return next_state
    return None


def eq(left: Any, right: Any) -> Goal:
    def goal(state: State) -> Iterable[State]:
        next_state = unify(left, right, state)
        if next_state is not None:
            yield next_state

    return goal


def succeed(state: State) -> Iterable[State]:
    yield state


def fail(_state: State) -> Iterable[State]:
    return
    yield  # pragma: no cover


def conj(*goals: Goal) -> Goal:
    def goal(state: State) -> Iterable[State]:
        states: Iterable[State] = (state,)
        for inner in goals:
            states = bind(states, inner)
        yield from states

    return goal


def disj(*goals: Goal) -> Goal:
    def goal(state: State) -> Iterable[State]:
        for inner in goals:
            yield from inner(state)

    return goal


def conde(*clauses: tuple[Goal, ...]) -> Goal:
    return disj(*(conj(*clause) for clause in clauses))


def bind(states: Iterable[State], goal: Goal) -> Generator[State, None, None]:
    for state in states:
        yield from goal(state)


def reify(term: Any, state: State) -> Any:
    term = walk(term, state)
    if isinstance(term, tuple):
        return tuple(reify(item, state) for item in term)
    if isinstance(term, list):
        return [reify(item, state) for item in term]
    if isinstance(term, dict):
        return {key: reify(value, state) for key, value in term.items()}
    return term


def run(limit: int | None, query: Any, goal: Goal) -> list[Any]:
    results: list[Any] = []
    for state in goal({}):
        results.append(reify(query, state))
        if limit is not None and len(results) >= limit:
            break
    return results
