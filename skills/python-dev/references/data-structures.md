# Python Data Structures: Dataclasses, NamedTuples, Comprehensions, Generators

## Data Classes

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class User:
    """User entity - auto-generates __init__, __repr__, __eq__."""
    id: str
    name: str
    email: str
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True

user = User(id="123", name="Alice", email="alice@example.com")

```

### With Validation

```python
@dataclass
class User:
    email: str
    age: int

    def __post_init__(self):
        if "@" not in self.email:
            raise ValueError(f"Invalid email: {self.email}")
        if not (0 <= self.age <= 150):
            raise ValueError(f"Invalid age: {self.age}")

```

## Named Tuples

```python
from typing import NamedTuple

class Point(NamedTuple):
    """Immutable 2D point."""
    x: float
    y: float

    def distance(self, other: 'Point') -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

p1, p2 = Point(0, 0), Point(3, 4)
print(p1.distance(p2))  # 5.0

```

## List Comprehensions

```python
# Simple transformations
names = [user.name for user in users if user.is_active]

# X Complex comprehensions - expand to a function instead
result = [x * 2 for x in items if x > 0 if x % 2 == 0]  # hard to read

# Use a regular function for multi-condition logic
def filter_and_double(items: list[int]) -> list[int]:
    return [x * 2 for x in items if x > 0 and x % 2 == 0]

```

## Generator Expressions

```python
# Generator - lazy, no intermediate list
total = sum(x * x for x in range(1_000_000))

# X List comprehension - creates full list in memory first
total = sum([x * x for x in range(1_000_000)])

```

## Generator Functions

```python
from typing import Iterator

def read_large_file(path: str) -> Iterator[str]:
    """Yield lines one at a time - O(1) memory."""
    with open(path) as f:
        for line in f:
            yield line.strip()

for line in read_large_file("huge.txt"):
    process(line)

```

## Memory Efficiency with **slots**

```python
# X Regular class - uses __dict__ for each instance
class Point:
    def __init__(self, x: float, y: float):
        self.x, self.y = x, y

# __slots__ - pre-allocates fixed attribute storage (lower memory)
class Point:
    __slots__ = ["x", "y"]

    def __init__(self, x: float, y: float):
        self.x, self.y = x, y

```

## String Building in Loops

```python
# X O(n²) - strings are immutable, each += creates a new object
result = ""
for item in items:
    result += str(item)

# O(n) - join is always faster for loops
result = "".join(str(item) for item in items)

```