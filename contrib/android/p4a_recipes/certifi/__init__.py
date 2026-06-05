from pythonforandroid.recipe import PythonRecipe


assert PythonRecipe.depends == ['python3']
assert PythonRecipe.python_depends == []


class CertifiRecipePinned(PythonRecipe):
    version = "2026.5.20"
    sha512sum = "160bb8f2e93e9f40adaed29bed755b7844503e27096a3d9683fbebcd08aa4470db40b785faf27f47a71ea7a9b8cb1febb5c4660ba58bb8e386ffa6af8dab165b"
    url = "https://pypi.python.org/packages/source/c/certifi/certifi-{version}.tar.gz"
    depends = ["setuptools"]


recipe = CertifiRecipePinned()
