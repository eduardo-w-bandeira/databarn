# # Original formula
# class AMeta(type):
#     def __new__(cls, name, bases, dct):
#         new_class = super().__new__(cls, name, bases, dct)
#         if bases and bases[0] == A:
#             for name, value in new_class.__dict__.items():
#                 if not name.startswith("_"):
#                     print(f"Found {name}={value}")
#             new_class.dna = []
#         return new_class


# class A(metaclass=AMeta):
#     pass


# class B(A):
#     b_attr = 3
#     b_attr_other = 4

# # To deploy


# class SeedMeta(type):
#     def __new__(cls, name, bases, dct):
#         new_class = super().__new__(cls, name, bases, dct)
#         if bases and bases[0] == BaseSeed:
#             for name, value in new_class.__dict__.items():
#                 if not name.startswith("_"):
#                     print(f"Found {name}={value}")
#             new_class.dna = []
#         return new_class


# class BaseSeed(metaclass=SeedMeta):
#     pass


# class Seed(metaclass=SeedMeta):
#     ...

# # tests


# class SeedMeta(type):
#     def __new__(cls, name, bases, dct):
#         new_class = super().__new__(cls, name, bases, dct)
#         if bases and bases[0] == Seed:
#             SeedMeta.wiz(new_class)
#         return new_class

#     @staticmethod
#     def wiz(new_class):
#         for name, value in new_class.__dict__.items():
#             if not name.startswith("_"):
#                 print(f"{name}={value}")
#         new_class.dna = []


# class Seed(metaclass=SeedMeta):
#     a = 1


# class Derived(Seed):
#     b = 2


# class DerivedDerived(Derived):
#     c = 3

# # Third is working
# class SeedMeta(type):
#     def __new__(cls, name, bases, dct):
#         new_class = super().__new__(cls, name, bases, dct)
#         if name != 'Seed':  # Skip for the Seed class itself
#             SeedMeta.wiz(new_class)
#         return new_class

#     @staticmethod
#     def wiz(new_class):
#         for name, value in new_class.__dict__.items():
#             if not name.startswith("_"):
#                 print(f"{name}={value}")
#         new_class.dna = []


# class Seed(metaclass=SeedMeta):
#     a = 1


# class Derived(Seed):
#     b = 2


# class DerivedDerived(Derived):
#     c = 3

# Fourth is working
class SeedMeta(type):
    def __new__(cls, name, bases, dct):
        new_class = super().__new__(cls, name, bases, dct)
        if name != 'Seed':  # Skip for the Seed class itself
            SeedMeta.wiz(new_class)
        return new_class

    @staticmethod
    def wiz(new_class):
        new_class.dna = []

        # Accumulate values from base classes
        for base in new_class.__bases__:
            if hasattr(base, 'dna'):
                new_class.dna.extend(base.dna)

        # Add values from the current class
        for name, value in new_class.__dict__.items():
            if not name.startswith("_") and name != 'dna':
                print(f"{name}={value}")
                new_class.dna.append((name, value))


class Seed(metaclass=SeedMeta):
    a = 1


class Derived(Seed):
    b = 2


class DerivedDerived(Derived):
    c = 3


# Test the classes
print("Derived.dna:", Derived.dna)
print("DerivedDerived.dna:", DerivedDerived.dna)
