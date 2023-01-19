import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

import keypirinha as kp
import keypirinha_util as kpu
import winreg
import collections
import json
import subprocess
from datetime import datetime
import timeago

_Project = collections.namedtuple(
    "Project",
    (
        "name",
        "path",
        "version",
        "is_version_exists",
        "is_favorite",
        "date_modified",
    )
)
_Editor = collections.namedtuple(
    "Editor",
    (
        "path",
        "version",
    )
)

def _strike_through(text):
    out = ''
    for ch in text:
        out += ch + '\u0335'
    return out

class UnityEngine(kp.Plugin):
    """
    One-line description of your plugin.

    This block is a longer and more detailed description of your plugin that may
    span on several lines, albeit not being required by the application.

    You may have several plugins defined in this module. It can be useful to
    logically separate the features of your package. All your plugin classes
    will be instantiated by Keypirinha as long as they are derived directly or
    indirectly from :py:class:`keypirinha.Plugin` (aliased ``kp.Plugin`` here).

    In case you want to have a base class for your plugins, you must prefix its
    name with an underscore (``_``) to indicate Keypirinha it is not meant to be
    instantiated directly.

    In rare cases, you may need an even more powerful way of telling Keypirinha
    what classes to instantiate: the ``__keypirinha_plugins__`` global variable
    may be declared in this module. It can be either an iterable of class
    objects derived from :py:class:`keypirinha.Plugin`; or, even more dynamic,
    it can be a callable that returns an iterable of class objects. Check out
    the ``StressTest`` example from the SDK for an example.

    Up to 100 plugins are supported per module.

    More detailed documentation at: http://keypirinha.com/api/plugin.html
    """

    ITEMCAT_PROJECT_LIST = kp.ItemCategory.USER_BASE + 1
    ITEMCAT_PROJECT = kp.ItemCategory.USER_BASE + 2
    ITEMCAT_EDITOR_REPORT_LIST = kp.ItemCategory.USER_BASE + 3
    ITEMCAT_EDITOR_REPORT = kp.ItemCategory.USER_BASE + 4

    projects = []
    editors = dict()
    hubExePath = None

    def __init__(self):
        super().__init__()

    def on_start(self):
        # self._cache_data()

        # self.set_actions(self.ITEMCAT_PROJECTS, [
        #     self.create_action(
        #         name=
        #     )
        # ])
        pass


    def _get_project_items(self):
        items = []
        projects = sorted(self.projects, key=lambda p:(p.is_favorite,p.date_modified), reverse=True)
        for project in projects:
            fav_str = "★" if project.is_favorite else ""

            version_str = ''
            if project.is_version_exists:
                version_str = f"{project.version: <11}"
            else:
                version_str = f"{_strike_through(project.version): <22}"

            items.append(self.create_item(
                category=self.ITEMCAT_PROJECT,
                label=f"Unity Project: {project.name} {fav_str}",
                short_desc=f"{version_str}\t\t\t\t{project.path}",
                target=project.path,
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.NOARGS,
                data_bag=json.dumps(project)
            ))

        return items

    def _get_editor_items(self):
        items = []
        projects = sorted(self.projects, key=lambda p:(p.version, p.date_modified), reverse=True)
        for project in projects:
            if not project.is_version_exists:
                continue

            items.append(self.create_item(
                category=self.ITEMCAT_PROJECT,
                label=f"{project.version}\t\t\t\t{project.name}",
                short_desc=f"{timeago.format(project.date_modified, datetime.now())}",
                target=project.path,
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.NOARGS,
                # data_bag=json.dumps(project)
            ))

        for project in projects:
            if project.is_version_exists:
                continue

            items.append(self.create_item(
                category=self.ITEMCAT_PROJECT,
                label=f"{_strike_through(project.version)}\t\t\t\t{project.name}",
                short_desc=f"{timeago.format(project.date_modified, datetime.now())}",
                target=project.path,
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.NOARGS,
                # data_bag=json.dumps(project)
            ))

        return items

    def on_catalog(self):
        self._cache_data()

        catalog = []

        catalog.append(self.create_item(
            category=self.ITEMCAT_PROJECT_LIST,
            label="Unity Projects",
            short_desc="Launch Unity Projects",
            target="projects",
            args_hint=kp.ItemArgsHint.ACCEPTED,
            hit_hint=kp.ItemHitHint.KEEPALL
        ))

        catalog.append(self.create_item(
            category=self.ITEMCAT_EDITOR_REPORT_LIST,
            label="Unity Editors Report",
            short_desc="Unity Editors Report",
            target="editors report",
            args_hint=kp.ItemArgsHint.ACCEPTED,
            hit_hint=kp.ItemHitHint.KEEPALL
        ))

        catalog.extend(self._get_project_items())

        self.set_catalog(catalog)
        # self.set_catalog([])

    def on_suggest(self, user_input, items_chain):
        if not items_chain:
            return

        closest_cat=items_chain[-1].category()

        if closest_cat == self.ITEMCAT_PROJECT_LIST:
            user_input = user_input.strip()

            self.set_suggestions(
                self._get_project_items(),
                kp.Match.ANY if not user_input else kp.Match.FUZZY,
                kp.Sort.NONE if not user_input else kp.Sort.SCORE_DESC
                # kp.Sort.NONE
            )

        if closest_cat == self.ITEMCAT_EDITOR_REPORT_LIST:
            self.set_suggestions(
                self._get_editor_items(),
                kp.Match.ANY,
                kp.Sort.NONE
            )
            pass

    def on_execute(self, item, action):
        if item.category() != self.ITEMCAT_PROJECT:
            return

        project = _Project(*json.loads(item.data_bag()))

        exePath = self.hubExePath
        if project.version in self.editors:
            exePath = self.editors[project.version].path
        else:
            #self.err(f"Unity version {project.Version} not found")
            pass

        if exePath is None:
            self.err(f"Unity version {project.Version} and Unity Hub not found")
            return

        try:
            subprocess.Popen([exePath, '-projectPath', project.path],
                            close_fds=True,
                            creationflags=subprocess.DETACHED_PROCESS)
        except Exception as e:
            self.err(str(e), "Could not start " + exePath);


    def on_activated(self):
        pass

    def on_deactivated(self):
        pass

    def on_events(self, flags):
        pass

    def _cache_data(self):
        self.projects = []
        self.editors = dict()


        hklm = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
        try:
            with winreg.OpenKey(hklm,r"SOFTWARE\Unity Technologies\Hub") as reg_key:
                self.hubExePath = os.path.join(winreg.QueryValueEx(reg_key, "InstallLocation")[0], "Unity Hub.exe")
        except:
            pass

        if not os.path.exists(self.hubExePath):
            self.err(f"Unity Hub not found at {self.hubExePath}")


        hubDataPath = os.path.join(os.getenv('APPDATA'), "UnityHub");

        favoriteProjects = set()
        try:
            with open(os.path.join(hubDataPath, "favoriteProjects.json")) as file:
                favoriteProjectsJson = file.read().replace("\\\"", "\"").strip("\"").replace("\\\\", "\\")
                favoriteProjects.update(json.loads(favoriteProjectsJson))
        except IOError as e:
            self.err("I/O error({0}): {1}".format(e.errno, e.strerror))



        editorsLocations = [
            r"C:\Program Files\Unity\Hub\Editor\\",
        ]
        secondaryInstallPathFilePath = os.path.join(hubDataPath, "secondaryInstallPath.json")
        if os.path.exists(secondaryInstallPathFilePath):
            try:
                with open(secondaryInstallPathFilePath) as file:
                    secondaryEditorsLocation = file.read().replace("\\\"", "\"").strip("\"").replace("\\\\", "\\")
                    editorsLocations.append(secondaryEditorsLocation)
            except IOError as e:
                self.err("I/O error({0}): {1}".format(e.errno, e.strerror))

        for editorsLocation in editorsLocations:
            for editorLocation in [f.path for f in os.scandir(editorsLocation) if f.is_dir()]:
                version = os.path.basename(editorLocation);
                exePath = os.path.join(editorLocation, "Editor", "Unity.exe");
                if not os.path.exists(exePath):
                    continue

                self.editors[version] = _Editor (
                    path    = exePath,
                    version = version,
                )



        projectsPath = None
        try:
            with open(os.path.join(hubDataPath, "projectDir.json")) as file:
                projectsPath = json.loads(file.read())["directoryPath"]
        except IOError as e:
            self.err("I/O error({0}): {1}".format(e.errno, e.strerror))

        projectPaths = set();
        if projectsPath is not None:
            projectPaths.update([f.path for f in os.scandir(projectsPath) if f.is_dir()]);

        hkcu = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        with winreg.OpenKey(hkcu,r"SOFTWARE\Unity Technologies\Unity Editor 5.x") as reg_key:
            key_idx = 0
            while True:
                try:
                    value_name, value_data, _ = winreg.EnumValue(reg_key, key_idx)

                    if value_name.startswith("RecentlyUsedProjectPaths-"):
                        # project_paths.append(str(value_data, 'utf-8'))
                        path = value_data.decode().rstrip("\x00").replace("/","\\")
                        projectPaths.add(path)

                    key_idx += 1
                except OSError:
                    break

        for path in projectPaths:
            maybe_project = self.project_from_path(path, favoriteProjects)
            if maybe_project is not None:
                self.projects.append(maybe_project)


    def project_from_path(self, path, favoriteProjects):
        project_version_file_path = os.path.join(path, "ProjectSettings", "ProjectVersion.txt")
        if not os.path.exists(project_version_file_path):
            return None

        version = None
        try:
            with open(project_version_file_path, "r") as file:
                while True:
                    line = file.readline()
                    if not line:
                        break

                    line_data = line.split(": ")
                    if line_data[0] == "m_EditorVersion":
                        version = line_data[1].strip()
                        break
        except IOError as e:
            self.err("I/O error({0}): {1}".format(e.errno, e.strerror))

        if version is None:
            return None

        return _Project(
            name            = os.path.basename(path),
            path            = path,
            version         = version,
            is_version_exists = version in self.editors,
            date_modified    = os.path.getmtime(path),
            is_favorite      = path in favoriteProjects
        );
