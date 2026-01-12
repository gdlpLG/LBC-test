import lbc
print("Categories:")
for c in lbc.Category:
    print(f" - {c.name}: {c.value}")

print("\nDefault category check:")
try:
    print(f"None category test:")
    # This might tell us if passing None to something that calls .value fails
    class Mock:
        def __init__(self, cat):
            self.cat = cat
        def run(self):
            return self.cat.value
    
    m = Mock(None)
    m.run()
except Exception as e:
    print(f"Caught expected error: {e}")
