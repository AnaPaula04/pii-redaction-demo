
#!/usr/bin/env python3
"""
Python Basics Exercises
Run: python exercises/python_basics_exercises.py
Fill the TODOs and print results to verify my understanding.
"""

# 1) Variables and types
# TODO: Create variables: name (str), age (int), height_m (float)
name = "Ana"  # TODO: change if you want
age = 32      # TODO
height_m = 1.57  # TODO
print("1) name:", name, "| age:", age, "| height_m:", height_m)

# 2) Lists & loops
dogs = ["Goldie", "Benji"]
# TODO: Append one more dog name
dogs.append("Daisy")
for i, dog in enumerate(dogs, start=1):
    print(f"2) Dog #{i}:", dog)

# 3) Dicts
profile = {
    "first_name": "Ana",
    "city": "Chicago",
    "languages": ["Portuguese", "English", "Spanish"],
}
# TODO: Add a new key "goal" with value "Become a software engineer"
profile["goal"] = "Become a software engineer"
print("3) profile keys:", list(profile.keys()))
print("3) goal:", profile.get("goal"))

# 4) Functions
# TODO: Write a function bmi(weight_kg, height_m) -> float
def bmi(weight_kg, height_m):
    return weight_kg / (height_m ** 2)

print("4) BMI for 62kg, 1.57m:", round(bmi(62, 1.57), 2))

# 5) File I/O
# TODO: Write a small text file 'scratch.txt' with one line 
with open("scratch.txt","w") as f:
    f.write("Hello, Python, this is Ana\n")
# TODO: Read it back and print
with open("scratch.txt","r") as f:
    content = f.read().strip()
print("5) File content:", content)

# 6) Classes (OOP)
# TODO: Define a class Counter with methods inc(), dec(), value()
class Counter:
    def __init__(self, start=0):
        self._v = start
    def inc(self):
        self._v += 1
    def dec(self):
        self._v -= 1
    def value(self):
        return self._v

c = Counter()
c.inc(); c.inc(); c.dec()
print("6) Counter value should be 1:", c.value())

print("\nAll basic exercises ran. I can always try editing values and adding different tests!")
