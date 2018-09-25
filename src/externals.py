import os
import re
from os import path
import yaml

from src.github import assert_valid_git_hub_url

root_folder = path.normpath(path.join(os.path.dirname(__file__), '..'))


class ExternalMount:

    def __init__(self, build_mode, external_spec):
        self.build_mode = build_mode

        print("Detected external: ", external_spec)
        self.external_base: str = external_spec['base']
        self.external_path: str = external_spec['path']
        self.external_nav: str = external_spec['nav']
        self.external_repo: str = external_spec['repo']
        self.external_branch: str = external_spec['branch']

        assert_valid_git_hub_url(self.external_repo, 'EXTERNAL MODULE: %s' % self.external_path)

        self.target_external_path = path.join(root_folder, 'pages', self.external_base.lstrip("/"))
        self.source_external_path = path.join(root_folder, 'external', self.external_path.lstrip("/"))

        self.nav_file = path.join(self.source_external_path, self.external_nav.lstrip("/"))

        print("External repo:       ", self.external_repo)
        print("External nav file:   ", self.nav_file)
        print("External source dir: ", self.source_external_path)
        print("External target dir: ", self.target_external_path)


def _rant_if_external_nav_is_not_found(self: ExternalMount):
    if os.path.isfile(self.nav_file):
        return True

    if self.build_mode:
        raise Exception("File " + self.nav_file + " is not found, clone "
                        + self.external_repo + " to " + self.source_external_path)
    else:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!!! Cannot locate external sources for path ")
        print("!!!! " + self.external_path)
        print("!!!! Please make sure you checked out the external repository")
        print("!!!! " + self.external_repo)
        print("!!!! to ")
        print("!!!! " + self.source_external_path)
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        return False


class ExternalItem:

    def __init__(self, module, url_mappers, item):
        self.module = module
        self.url_mappers = url_mappers

        self.title: str = item['title']
        self.url: str = item['url']
        self.md: str = item['md']
        self.html = module.external_base.rstrip("/") + "/" + self.url.lstrip("/")

        assert self.md.endswith(".md"), "md path " + self.md + " must have `.md` extension"
        assert self.url.endswith(".html"), "url path " + self.url + "must have `.html` " \
                                                                    "extension, no matter you have " \
                                                                    "`.md` file instead "

        self.ext_fix = re.compile('\.html$')
        self.source_item = path.join(module.source_external_path, self.md.lstrip('/'))
        self.target_name = self.ext_fix.sub(".md", self.url.lstrip('/'))
        self.target_item = path.join(module.target_external_path, self.target_name)
        self.target_dir = os.path.dirname(self.target_item)
        self.github_edit_url = \
            module.external_repo.rstrip('/') + "/edit/" + module.external_branch + "/" + self.md.lstrip("/")


    def generate_header(self):
        return "##################################################\n" \
               "#### THIS FILE WAS AUTOGENERATED FROM\n"              \
               "#### " + self.module.external_repo + "\n"             \
               "#### branch " + self.module.external_branch + "\n"    \
               "#### file   " + self.md + "\n"                        \
               "#### links were in the file! \n"                      \
               "#### HEADER below IS GENERATED! \n"                   \
               "##################################################\n" \
               "\n"                                                   \
               "---\n"                                                \
               "type: doc \n"                                         \
               "layout: reference \n"                                 \
               "title: \"" + self.title + "\"\n"                      \
               "github_edit_url: " + self.github_edit_url + "\n"      \
               "---\n\n"                                              \



def _process_external_entry(self: ExternalMount, url_mappers, entry: dict):
    item = ExternalItem(self, url_mappers, entry)

    if not os.path.isdir(item.target_dir):
        os.makedirs(item.target_dir, mode=0o777)

    with open(item.source_item, 'r') as file:
        source_text = file.read()

    # TODO: check `---` headers at the beginning of the original file and WARN or MERGE

    for mapper in url_mappers:
        source_text = mapper(source_text)

    template = item.generate_header()

    source_text = template + source_text

    with open(item.target_item, 'w') as file:
        file.write(source_text)

    return {
        'url': item.html,
        'title': item.title
    }


def _build_url_mappers(external_yml):
    def _url_replace_function(source_url, target_url):
        pattern = "\\]\\("        "(" + re.escape(source_url) + ")"           "(#[^\\)]+)?"     "\\)"
        return lambda text: re.compile(pattern).sub("](" + target_url + "\\2)", text)

    return [_url_replace_function(item['md'], item['url']) for item in external_yml]


def _process_external_key(build_mode, data):
    if 'external' not in data: return
    mount = ExternalMount(build_mode, data['external'])
    del data['external']

    if not _rant_if_external_nav_is_not_found(mount):
        data['content'] = [{ 'url': '/', 'title': 'external "%s" is it included' % mount.external_path}]
        return

    with open(mount.nav_file) as stream:
        external_yml = yaml.load(stream)
        assert isinstance(external_yml, list)

    url_mappers = _build_url_mappers(external_yml)
    data['content'] = [_process_external_entry(mount, url_mappers, item) for item in external_yml]


def process_nav_includes(build_mode, data):
    if isinstance(data, list):
        for item in data:
            process_nav_includes(build_mode, item)

    if isinstance(data, dict):
        _process_external_key(build_mode, data)

        for item in data.values():
            process_nav_includes(build_mode, item)
