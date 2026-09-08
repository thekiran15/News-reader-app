from pythonforandroid.recipes.freetype import FreetypeRecipe as OrigFreetypeRecipe


class FreetypeRecipe(OrigFreetypeRecipe):
    # Original savannah.gnu.org URL gets 502/504'd from GitHub Actions IPs.
    # Use Savannah's dedicated high-traffic mirror instead.
    url = 'https://download-mirror.savannah.gnu.org/releases/freetype/freetype-{version}.tar.gz'


recipe = FreetypeRecipe()