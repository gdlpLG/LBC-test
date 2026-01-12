import lbc
try:
    print("OwnerTypes:")
    for o in lbc.OwnerType:
        print(f" - {o.name}: {o.value}")
except:
    print("lbc.OwnerType not iterable or not found")

try:
    print("\nSorts:")
    for s in lbc.Sort:
        print(f" - {s.name}: {s.value}")
except:
    print("lbc.Sort not iterable or not found")
