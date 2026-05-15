# 1. Record architecture decisions

Date: 2026-05-15

## Status

Accepted

## Context

I want a durable record of why the system looks the way it does. Code shows
what we built, but not the tradeoffs behind it. For a project meant to show how
I reason about systems, that reasoning is the point.

## Decision

Use Architecture Decision Records. One file per decision, numbered in order,
written in plain language. A record captures the context, the decision, and the
consequences. Records are immutable once accepted. When a decision changes, we
add a new record that supersedes the old one.

## Consequences

Decisions live next to the code and survive turnover. The cost is a small habit
of writing a short note whenever we make a call that future readers would
otherwise have to reverse engineer.
