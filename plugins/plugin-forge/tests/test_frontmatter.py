import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pluginforge.rules import frontmatter

def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

class TestFrontmatter(unittest.TestCase):
    def test_skill_ok(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "skills", "x", "SKILL.md"), "---\nname: x\ndescription: y\n---\n# X\n")
            self.assertEqual(frontmatter.check(d, strict=False), [])

    def test_skill_missing_frontmatter(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "skills", "x", "SKILL.md"), "# X, no frontmatter\n")
            out = frontmatter.check(d, strict=False)
            self.assertTrue(any(f.severity == "HARD" for f in out))

    def test_skill_frontmatter_missing_keys(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "skills", "x", "SKILL.md"), "---\nname: x\n---\n# X\n")
            out = frontmatter.check(d, strict=False)
            self.assertTrue(any("name + description" in f.detail for f in out))

    def test_command_missing_description_is_soft(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "commands", "c.md"), "# c, no frontmatter\n")
            out = frontmatter.check(d, strict=False)
            self.assertTrue(out and all(f.severity == "SOFT" for f in out))

if __name__ == "__main__":
    unittest.main()
