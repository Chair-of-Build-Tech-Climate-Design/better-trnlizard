"""Lizard_Updater: update from a GitHub repository through trnlizard_manifest.json.

The source classification, URLs, manifest, retry/fallback decisions and the cache plan are pure Python and are tested
directly.  The glue (syncGitHubSource, resolveSource) runs here with the download function replaced by a fake GitHub and
a temporary cache folder; the .NET download itself (httpGetText) needs Rhino and is not covered.  tools/build_manifest.py
is checked against the updater's hash and the committed manifest.
"""

import base64
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
UPDATER_SOURCE = REPO_ROOT / "Lizard_Updater.py"
TOOL_SOURCE = REPO_ROOT / "tools" / "build_manifest.py"
SHA = "0123456789abcdef0123456789abcdef01234567"
DEFAULT_OWNER = "Chair-of-Build-Tech-Climate-Design"


def load_updater():
    """Lizard_Updater.py with System, Rhino, Grasshopper and scriptcontext stubbed (no ghenv: the entry point does not run)."""
    grasshopper = ModuleType("Grasshopper")
    grasshopper.Kernel = ModuleType("Grasshopper.Kernel")
    modules = {name: ModuleType(name) for name in ("System", "Rhino", "scriptcontext")}
    modules.update({"Grasshopper": grasshopper, "Grasshopper.Kernel": grasshopper.Kernel})
    modules["scriptcontext"].sticky = {}
    with mock.patch.dict(sys.modules, modules):
        spec = importlib.util.spec_from_file_location("Lizard_Updater_github", UPDATER_SOURCE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


def load_tool():
    spec = importlib.util.spec_from_file_location("build_manifest_under_test", TOOL_SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


UPDATER = load_updater()


# ---------------------------------------------------------------------------------------------------------------------
# pure logic
# ---------------------------------------------------------------------------------------------------------------------

class SourceClassificationTests(unittest.TestCase):
    def github(self, source):
        info = UPDATER.parseSource(source)
        self.assertEqual("github", info["kind"], source)
        return info["owner"], info["repo"], info["ref"]

    def test_not_connected_or_empty_is_the_default_repository(self):
        for source in (None, "", "   ", '""'):
            self.assertEqual((DEFAULT_OWNER, "better-trnlizard", "main"), self.github(source))
        self.assertEqual((DEFAULT_OWNER, "better-trnlizard", "main"), self.github(UPDATER.DEFAULT_SOURCE))

    def test_github_url_forms(self):
        for source in ("https://github.com/o/r", "https://github.com/o/r/", "https://github.com/o/r.git",
                       "http://www.github.com/o/r", "HTTPS://GitHub.com/o/r", "https://github.com:443/o/r",
                       "github.com/o/r", "www.github.com/o/r", "git@github.com:o/r.git", "git@github.com:o/r",
                       "ssh://git@github.com/o/r.git", "https://github.com/o/r?tab=readme", "https://github.com/o/r#readme",
                       '"https://github.com/o/r"', "  https://github.com/o/r  "):
            self.assertEqual(("o", "r"), self.github(source)[:2], source)
            self.assertEqual("main", self.github(source)[2], source)
        self.assertEqual(("My-Org", "my.repo_1"), self.github("https://github.com/My-Org/my.repo_1")[:2])

    def test_ref_from_tree_or_commit_suffix(self):
        self.assertEqual("dev", self.github("https://github.com/o/r/tree/dev")[2])
        self.assertEqual("feature/x-1", self.github("https://github.com/o/r/tree/feature/x-1")[2])
        self.assertEqual("v1.2.0", self.github("github.com/o/r/tree/v1.2.0/")[2])
        self.assertEqual(SHA, self.github("https://github.com/o/r/commit/" + SHA)[2])
        self.assertEqual("abc1234", self.github("https://github.com/o/r/commit/abc1234")[2])

    def test_local_paths(self):
        for path in (r"C:\Users\me\TRNLizard", "C:/Users/me/TRNLizard", r"\\tsclient\home\TRNLizard",
                     "//server/share/TRNLizard", "/home/me/TRNLizard", "relative/folder", r"D:\github.com\o\r",
                     "github.community/o/r", "C:"):
            info = UPDATER.parseSource(path)
            self.assertEqual({"kind": "folder", "path": path}, info, path)
        self.assertEqual(r"C:\my folder", UPDATER.parseSource(r'"C:\my folder"')["path"])

    def test_invalid_sources(self):
        cases = {
            "https://gitlab.com/o/r": "only GitHub",
            "http://example.com/github.com/o/r": "only GitHub",
            "https://github.com.evil.com/o/r": "only GitHub",
            "ftp://github.com/o/r": "only GitHub",
            "https://github.com/o": "names no repository",
            "https://github.com": "names no repository",
            "https://github.com/o/r/blob/main/Lizard_Hygro.py": "cannot tell the branch",
            "https://github.com/o/r/tree/": "cannot tell the branch",
            "https://github.com/o/r/commit/xyz": "cannot tell the branch",
            "https://github.com/o/r/tree/a..b": "invalid branch",
            "https://github.com/o/r/tree/a~1": "invalid branch",
            "https://github.com/o/../x": "invalid owner or repository",
        }
        for source, fragment in cases.items():
            with self.assertRaises(ValueError, msg=source) as caught:
                UPDATER.parseSource(source)
            self.assertIn(fragment, str(caught.exception), source)

    def test_ref_validation_and_commit_sha(self):
        self.assertTrue(UPDATER.isValidRef("feature/x"))
        for ref in ("", "a b", "a..b", "a:b", "a\\b", "a@{1}", "a*"):
            self.assertFalse(UPDATER.isValidRef(ref), ref)
        self.assertTrue(UPDATER.isCommitSha(SHA))
        self.assertTrue(UPDATER.isCommitSha(SHA.upper()))
        self.assertFalse(UPDATER.isCommitSha(SHA[:-1]))
        self.assertFalse(UPDATER.isCommitSha("main"))
        self.assertFalse(UPDATER.isCommitSha(None))


class UrlAndCacheNameTests(unittest.TestCase):
    def test_sanitize_ref(self):
        self.assertEqual("main", UPDATER.sanitizeRef("main"))
        self.assertEqual("v1.2.0", UPDATER.sanitizeRef("v1.2.0"))
        slashed = UPDATER.sanitizeRef("feature/x")
        self.assertRegex(slashed, r"^feature_x-[0-9a-f]{8}$")
        self.assertNotEqual(slashed, UPDATER.sanitizeRef("feature_x"))
        self.assertEqual(slashed, UPDATER.sanitizeRef("feature/x"))
        self.assertRegex(UPDATER.sanitizeRef("a" * 100), r"^a{60}-[0-9a-f]{8}$")
        self.assertRegex(UPDATER.sanitizeRef("v1."), r"^v1-[0-9a-f]{8}$")   # no trailing dot on Windows
        self.assertEqual("o_r_main", UPDATER.cacheFolderName("o", "r", "main"))

    def test_raw_and_api_urls(self):
        self.assertEqual("https://raw.githubusercontent.com/o/r/main/trnlizard_manifest.json",
                         UPDATER.rawUrl("o", "r", "main", "trnlizard_manifest.json"))
        self.assertEqual("https://raw.githubusercontent.com/o/r/feature/x/Lizard_Hygro.py",
                         UPDATER.rawUrl("o", "r", "feature/x", "Lizard_Hygro.py"))
        self.assertEqual("https://raw.githubusercontent.com/o/r/a%20b%23c/x.py", UPDATER.rawUrl("o", "r", "a b#c", "x.py"))
        self.assertEqual("https://raw.githubusercontent.com/o/r/%C3%A4/x.py", UPDATER.rawUrl("o", "r", "\u00e4", "x.py"))
        self.assertEqual("https://api.github.com/repos/o/r/commits/main", UPDATER.commitApiUrl("o", "r", "main"))


class HttpDecisionTests(unittest.TestCase):
    def test_failure_texts(self):
        text = UPDATER.describeHttpFailure("u", 404, "x")
        self.assertIn("repository or ref not found, or the repository is private", text)
        for status in (429, 403):
            self.assertIn("GitHub rate limit (HTTP {0}) - try again later or set source to a local folder".format(status),
                          UPDATER.describeHttpFailure("u", status, "x"))
        self.assertIn("no answer (timed out)", UPDATER.describeHttpFailure("u", None, "timed out"))
        self.assertIn("HTTP 500 (boom)", UPDATER.describeHttpFailure("u", 500, "boom"))

    def test_retry_after_header(self):
        self.assertEqual(5.0, UPDATER.parseRetryAfter("5"))
        self.assertEqual(2.5, UPDATER.parseRetryAfter(" 2.5 "))
        self.assertEqual(0.0, UPDATER.parseRetryAfter("-3"))
        self.assertIsNone(UPDATER.parseRetryAfter(None))
        self.assertIsNone(UPDATER.parseRetryAfter("Wed, 21 Oct 2026 07:28:00 GMT"))

    def test_retry_delay(self):
        delay = UPDATER.retryDelay
        self.assertEqual(1.0, delay(429, None, 1, 0.0))
        self.assertEqual(2.0, delay(429, None, 2, 1.0))
        self.assertIsNone(delay(429, None, 3, 3.0))           # RETRY_ATTEMPTS tries in all
        for status in (502, 503, 504):
            self.assertEqual(1.0, delay(status, None, 1, 0.0))
        for status in (None, 400, 403, 404, 500):            # 403: the API limit resets after an hour, no use waiting
            self.assertIsNone(delay(status, None, 1, 0.0), status)
        self.assertEqual(4.0, delay(429, 4.0, 1, 0.0))        # Retry-After is honoured
        self.assertEqual(0.0, delay(503, 0.0, 1, 0.0))
        self.assertIsNone(delay(429, 30.0, 1, 0.0))           # longer than the cap: give up at once
        self.assertIsNone(delay(429, 2.0, 2, 9.0))            # total wait capped at MAX_RETRY_WAIT_S
        self.assertEqual(10.0, UPDATER.MAX_RETRY_WAIT_S)

    def test_cache_fallback_decision(self):
        for status in (None, 403, 429, 500, 502, 503):
            self.assertTrue(UPDATER.canUseCache(status), status)
        for status in (400, 401, 404, 410):
            self.assertFalse(UPDATER.canUseCache(status), status)


def manifest_text(scripts, generated="2026-10-21T10:00:00Z", fmt=1):
    files = {name: {"sha256": UPDATER.getHash(text), "size": len(text.encode("utf-8"))} for name, text in scripts.items()}
    return json.dumps({"format": fmt, "generated": generated, "files": files})


class ManifestTests(unittest.TestCase):
    def test_parse_valid_manifest(self):
        manifest = UPDATER.parseManifest(manifest_text({"Lizard_A.py": "a = 1\n", "Lizard_B.py": "b = 2\n"}))
        self.assertEqual(1, manifest["format"])
        self.assertEqual("2026-10-21T10:00:00Z", manifest["generated"])
        self.assertEqual(["Lizard_A.py", "Lizard_B.py"], sorted(manifest["files"]))
        self.assertEqual(UPDATER.getHash("a = 1"), manifest["files"]["Lizard_A.py"]["sha256"])
        self.assertEqual(6, manifest["files"]["Lizard_A.py"]["size"])
        upper = json.dumps({"format": 1, "files": {"X.py": {"sha256": "A" * 64}}})
        self.assertEqual({"sha256": "a" * 64, "size": None}, UPDATER.parseManifest(upper)["files"]["X.py"])
        self.assertIsNone(UPDATER.parseManifest(upper)["generated"])

    def test_unknown_files_are_ignored(self):
        good = {"sha256": "a" * 64, "size": 1}
        manifest = UPDATER.parseManifest(json.dumps({"format": 1, "files": {
            "X.py": good, "_X.py": good, "notes.txt": "anything", "trnlizard_presets.json": good}}))
        self.assertEqual(["X.py"], sorted(manifest["files"]))
        self.assertEqual(["_X.py", "notes.txt", "trnlizard_presets.json"], manifest["ignored"])

    def test_invalid_manifests(self):
        good = {"sha256": "a" * 64, "size": 1}
        cases = {
            "{not json": "not valid JSON",
            "[]": "not a JSON object",
            json.dumps({"files": {"X.py": good}}): "format",
            json.dumps({"format": True, "files": {"X.py": good}}): "format",
            json.dumps({"format": 0, "files": {"X.py": good}}): "format",
            json.dumps({"format": 2, "files": {"X.py": good}}): "newer than this updater",
            json.dumps({"format": 1, "files": {}}): "no files",
            json.dumps({"format": 1, "files": []}): "no files",
            json.dumps({"format": 1, "files": {"../X.py": good}}): "invalid file name",
            json.dumps({"format": 1, "files": {"sub/X.py": good}}): "invalid file name",
            json.dumps({"format": 1, "files": {"sub\\X.py": good}}): "invalid file name",
            json.dumps({"format": 1, "files": {"..": good}}): "invalid file name",
            json.dumps({"format": 1, "files": {"C:X.py": good}}): "invalid file name",
            json.dumps({"format": 1, "files": {"X.txt": good}}): "no files listed that this updater uses",
            json.dumps({"format": 1, "files": {"X.py": "abc"}}): "not an object",
            json.dumps({"format": 1, "files": {"X.py": {"sha256": "abc"}}}): "invalid sha256",
            json.dumps({"format": 1, "files": {"X.py": {"sha256": "g" * 64}}}): "invalid sha256",
            json.dumps({"format": 1, "files": {"X.py": {"sha256": "a" * 64, "size": -1}}}): "invalid size",
            json.dumps({"format": 1, "files": {"X.py": good, "x.py": good}}): "differ in case",
        }
        for text, fragment in cases.items():
            with self.assertRaises(ValueError, msg=text) as caught:
                UPDATER.parseManifest(text)
            self.assertIn(fragment, str(caught.exception), text)


class CachePlanTests(unittest.TestCase):
    FILES = {"A.py": {"sha256": "1" * 64}, "B.py": {"sha256": "2" * 64}, "C.py": {"sha256": "3" * 64}}

    def test_download_plan(self):
        download, unchanged = UPDATER.planDownloads(self.FILES, {"A.py": "1" * 64, "B.py": "9" * 64, "D.py": "4" * 64})
        self.assertEqual(["B.py", "C.py"], download)   # other hash, missing
        self.assertEqual(["A.py"], unchanged)
        download, unchanged = UPDATER.planDownloads(self.FILES, {"A.py": None})   # unreadable copy
        self.assertEqual(["A.py", "B.py", "C.py"], download)

    def test_removal_plan(self):
        self.assertEqual(["D.py", "_old.py", "a.py"], UPDATER.planRemovals(self.FILES, ["A.py", "a.py", "D.py", "_old.py"]))
        self.assertEqual([], UPDATER.planRemovals(self.FILES, ["A.py", "B.py"]))

    def test_removal_plan_includes_an_unlisted_icons_file(self):
        self.assertEqual(["trnlizard_icons.json"], UPDATER.planRemovals(self.FILES, ["A.py", "trnlizard_icons.json", "x.json"]))
        files = dict(self.FILES, **{"trnlizard_icons.json": {"sha256": "4" * 64}})
        self.assertEqual([], UPDATER.planRemovals(files, ["A.py", "trnlizard_icons.json"]))

    def test_other_cache_folders(self):
        caches = {"o_r_main", "o_r_feat_x-1234abcd", "other"}
        self.assertEqual(["o_r_feat_x-1234abcd"],
                         UPDATER.otherCacheFolders(["o_r_main", "o_r_feat_x-1234abcd", "other", "empty"], "o_r_main",
                                                   lambda name: name in caches and name != "other"))

    def test_cache_complete(self):
        complete = {"A.py": "1" * 64, "B.py": "2" * 64, "C.py": "3" * 64, "extra.py": "5" * 64}
        self.assertTrue(UPDATER.cacheIsComplete(self.FILES, complete))
        self.assertFalse(UPDATER.cacheIsComplete(self.FILES, {"A.py": "1" * 64, "B.py": "2" * 64}))
        self.assertFalse(UPDATER.cacheIsComplete(self.FILES, {"A.py": "1" * 64, "B.py": "2" * 64, "C.py": None}))

    def test_download_verification_ignores_line_endings_and_bom(self):
        text = "x = 1\ny = 2\n"
        expected = UPDATER.getHash(text)
        self.assertIsNone(UPDATER.verifyDownload("X.py", text, expected))
        self.assertIsNone(UPDATER.verifyDownload("X.py", "\ufeffx = 1\r\ny = 2\r\n  ", expected))
        problem = UPDATER.verifyDownload("X.py", "x = 2\n", expected)
        for fragment in ("X.py", "does not match the manifest", "not written", "build_manifest.py", "few minutes"):
            self.assertIn(fragment, problem)


class BuildManifestToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = load_tool()

    def test_hash_is_the_updaters(self):
        samples = ["", "x = 1", "x = 1\r\n", "\ufeffx = 1\n\n  \t", "a\rb\r\nc\n", "\u00e4\u00f6\u00fc = 'm\u00b2'\n"]
        for text in samples:
            self.assertEqual(UPDATER.normalizeCode(text), self.tool.normalizeCode(text))
            self.assertEqual(UPDATER.getHash(text), self.tool.getHash(text))
        for path in REPO_ROOT.glob("*.py"):
            text = path.read_bytes().decode("utf-8-sig")
            self.assertEqual(UPDATER.getHash(text), self.tool.getHash(text), path.name)

    def test_selects_the_scripts_of_find_scripts(self):
        expected = sorted(os.path.basename(p) for p in UPDATER.findScripts(str(REPO_ROOT), []).values())
        self.assertEqual(expected, self.tool.scriptNames(str(REPO_ROOT)))
        self.assertIn("Lizard_Updater.py", expected)

    def test_committed_manifest_is_up_to_date(self):
        manifest = self.tool.readManifest(str(REPO_ROOT / "trnlizard_manifest.json"))
        self.assertIsNotNone(manifest, "trnlizard_manifest.json is missing: run python tools/build_manifest.py")
        self.assertEqual([], self.tool.staleFiles(str(REPO_ROOT), manifest),
                         "trnlizard_manifest.json is out of date: run python tools/build_manifest.py")
        parsed = UPDATER.parseManifest((REPO_ROOT / "trnlizard_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(manifest["files"]), sorted(parsed["files"]))

    def test_generate_check_and_idempotence(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        (root / "Lizard_A.py").write_bytes(b"\xef\xbb\xbfa = 1\r\n")
        (root / "_private.py").write_text("x = 1\n", encoding="utf-8")
        (root / "notes.txt").write_text("x", encoding="utf-8")
        out = mock.patch("sys.stdout", new=__import__("io").StringIO())
        with out:
            self.assertEqual(1, self.tool.main(["--check", "--root", str(root)]))   # missing
            self.assertEqual(0, self.tool.main(["--root", str(root)]))
        path = root / "trnlizard_manifest.json"
        first = path.read_text(encoding="utf-8")
        data = json.loads(first)
        self.assertEqual(["Lizard_A.py"], list(data["files"]))
        self.assertEqual({"sha256": UPDATER.getHash("a = 1"), "size": 5}, data["files"]["Lizard_A.py"])
        self.assertRegex(data["generated"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        with out:
            self.assertEqual(0, self.tool.main(["--check", "--root", str(root)]))
            self.assertEqual(0, self.tool.main(["--root", str(root)]))
        self.assertEqual(first, path.read_text(encoding="utf-8"))   # same files: same text, same generated
        # another generated time alone does not make the manifest stale
        data["generated"] = "2000-01-01T00:00:00Z"
        path.write_text(json.dumps(data), encoding="utf-8")
        with out:
            self.assertEqual(0, self.tool.main(["--check", "--root", str(root)]))
        # a changed, added or removed script does
        (root / "Lizard_A.py").write_text("a = 2\n", encoding="utf-8")
        with out:
            self.assertEqual(1, self.tool.main(["--check", "--root", str(root)]))
            self.assertEqual(0, self.tool.main(["--root", str(root)]))
            self.assertEqual(0, self.tool.main(["--check", "--root", str(root)]))
        self.assertNotEqual("2000-01-01T00:00:00Z", json.loads(path.read_text(encoding="utf-8"))["generated"])
        (root / "Lizard_B.py").write_text("b = 1\n", encoding="utf-8")
        self.assertEqual(["Lizard_B.py"], self.tool.staleFiles(str(root), self.tool.readManifest(str(path))))
        (root / "Lizard_A.py").unlink()
        self.assertEqual(["Lizard_A.py", "Lizard_B.py"], self.tool.staleFiles(str(root), self.tool.readManifest(str(path))))


# ---------------------------------------------------------------------------------------------------------------------
# glue with a fake GitHub and a temporary cache
# ---------------------------------------------------------------------------------------------------------------------

class FakeGitHub:
    """fetch(url, accept) of the updater against an in-memory repository o/r with the branch main at SHA."""

    def __init__(self, scripts, generated="2026-10-21T10:00:00Z"):
        self.scripts = dict(scripts)
        self.generated = generated
        self.manifest_override = None
        self.served = {}          # file name -> text served instead of the real one (e.g. a stale raw cache)
        self.failures = {}        # url fragment -> list of SourceError to raise one after the other
        self.calls = []

    def fail(self, fragment, *statuses):
        self.failures[fragment] = [UPDATER.SourceError(UPDATER.describeHttpFailure(fragment, s, "fake"), s) for s in statuses]

    def __call__(self, url, accept):
        self.calls.append((url, accept))
        for fragment, errors in self.failures.items():
            if fragment in url and errors:
                raise errors.pop(0)
        if url == UPDATER.commitApiUrl("o", "r", "main"):
            assert accept == UPDATER.SHA_MEDIA_TYPE
            return SHA + "\n"
        for ref in (SHA, "main"):
            prefix = "https://raw.githubusercontent.com/o/r/{0}/".format(ref)
            if url.startswith(prefix):
                name = url[len(prefix):]
                if name == "trnlizard_manifest.json":
                    return self.manifest_override or manifest_text(self.scripts, self.generated)
                if name in self.served:
                    return self.served[name]
                if name in self.scripts:
                    return self.scripts[name]
        raise UPDATER.SourceError(UPDATER.describeHttpFailure(url, 404, "Not Found"), 404)

    def downloads(self):
        return sorted(url.rsplit("/", 1)[1] for url, _ in self.calls
                      if url.startswith("https://raw.") and url.endswith(".py"))


class IconsFileTests(unittest.TestCase):
    def test_manifest_may_list_the_icons_file(self):
        text = json.dumps({"format": 1, "files": {"A.py": {"sha256": "1" * 64}, "trnlizard_icons.json": {"sha256": "2" * 64}}})
        self.assertIn("trnlizard_icons.json", UPDATER.parseManifest(text)["files"])
        bad = json.dumps({"format": 1, "files": {"other.json": {"sha256": "2" * 64}}})
        self.assertRaises(ValueError, UPDATER.parseManifest, bad)

    def test_parse_icons(self):
        self.assertEqual({"Lizard_A": "iVBORw0KGgo="}, UPDATER.parseIcons('{"format": 1, "icons": {"Lizard_A": "iVBORw0KGgo="}}'))
        for text in ("[]", '{"icons": []}', '{"icons": {"A": "not base64!"}}', "nope"):
            with self.subTest(text=text):
                self.assertRaises(ValueError, UPDATER.parseIcons, text)

    def test_committed_icons_cover_every_component_script(self):
        icons = UPDATER.parseIcons((REPO_ROOT / "trnlizard_icons.json").read_text(encoding="utf-8"))
        scripts = sorted(p.stem for p in REPO_ROOT.glob("Lizard_*.py"))
        self.assertEqual([], [name for name in scripts if name not in icons])
        for name, data in icons.items():
            self.assertTrue(base64.b64decode(data).startswith(b"\x89PNG"), name)


class GitHubSyncTests(unittest.TestCase):
    SCRIPTS = {"Lizard_A.py": "a = 1\r\n", "Lizard_B.py": "\ufeffb = '\u00e4'\n", "Lizard_Updater.py": "u = 1\n"}

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.github = FakeGitHub(self.SCRIPTS)
        self.folder = os.path.join(self.root, "o_r_main")
        sleeper = mock.patch("time.sleep")
        self.sleep = sleeper.start()
        self.addCleanup(sleeper.stop)

    def sync(self, ref="main"):
        log, errors = [], []
        info = {"kind": "github", "owner": "o", "repo": "r", "ref": ref}
        folder = UPDATER.syncGitHubSource(info, log, errors, fetch=self.github, root=self.root)
        return folder, log, errors

    def cached(self):
        return sorted(name for name in os.listdir(self.folder))

    def test_first_sync_downloads_everything_by_commit(self):
        folder, log, errors = self.sync()
        self.assertEqual(self.folder, folder)
        self.assertEqual([], errors)
        self.assertEqual(["Lizard_A.py", "Lizard_B.py", "Lizard_Updater.py", "trnlizard_manifest.json"], self.cached())
        with open(os.path.join(folder, "Lizard_A.py"), "rb") as handle:
            self.assertEqual(b"a = 1\r\n", handle.read())   # written as downloaded
        self.assertEqual("b = '\u00e4'\n", UPDATER.readScript(os.path.join(folder, "Lizard_B.py")))
        self.assertTrue(all(SHA in url for url, _ in self.github.calls[1:]))   # manifest and files from one commit
        for line in ("Source: GitHub o/r, ref main", "Commit: " + SHA,
                     "Manifest generated: 2026-10-21T10:00:00Z (3 scripts)", "Downloaded: 3, unchanged: 0, removed: 0"):
            self.assertIn(line, log)
        self.assertEqual(["Lizard_A", "Lizard_B", "Lizard_Updater"], sorted(UPDATER.findScripts(folder, [])))
        self.assertFalse([name for name in os.listdir(folder) if name.endswith(".tmp")])

    def test_a_successful_sync_removes_the_caches_of_other_branches(self):
        old = os.path.join(self.root, "o_r_feature")
        foreign = os.path.join(self.root, "not_a_cache")
        os.makedirs(old)
        os.makedirs(foreign)
        with open(os.path.join(old, "trnlizard_manifest.json"), "w") as handle:
            handle.write("{}")
        folder, log, errors = self.sync()
        self.assertEqual([], errors)
        self.assertFalse(os.path.exists(old))
        self.assertTrue(os.path.isdir(foreign))   # no manifest: not ours, left alone
        self.assertIn("Removed the old cache folder o_r_feature", log)

    def test_second_sync_downloads_nothing(self):
        self.sync()
        self.github.calls = []
        folder, log, errors = self.sync()
        self.assertEqual([], errors)
        self.assertEqual([], self.github.downloads())
        self.assertEqual(2, len(self.github.calls))   # commit lookup and manifest
        self.assertIn("Downloaded: 0, unchanged: 3, removed: 0", log)

    def test_changed_added_and_removed_scripts(self):
        self.sync()
        with open(os.path.join(self.folder, "stray.py"), "w") as handle:
            handle.write("x = 1\n")
        with open(os.path.join(self.folder, "Lizard_A.py"), "w") as handle:   # a damaged cached copy
            handle.write("a = 0\n")
        self.github.scripts["Lizard_B.py"] = "b = 2\n"
        self.github.scripts["Lizard_C.py"] = "c = 1\n"
        del self.github.scripts["Lizard_Updater.py"]
        self.github.calls = []
        folder, log, errors = self.sync()
        self.assertEqual([], errors)
        self.assertEqual(["Lizard_A.py", "Lizard_B.py", "Lizard_C.py"], self.github.downloads())
        self.assertEqual(["Lizard_A.py", "Lizard_B.py", "Lizard_C.py", "trnlizard_manifest.json"], self.cached())
        self.assertIn("Downloaded: 3, unchanged: 0, removed: 2", log)
        self.assertIn("Removed from the cache: stray.py", log)
        self.assertEqual("b = 2\n", UPDATER.readScript(os.path.join(folder, "Lizard_B.py")))

    def test_hash_mismatch_is_an_error_and_nothing_is_written(self):
        self.sync()
        self.github.scripts["Lizard_A.py"] = "a = 2\n"
        self.github.scripts["Lizard_C.py"] = "c = 1\n"
        self.github.served["Lizard_C.py"] = "c = 'stale'\n"
        folder, log, errors = self.sync()
        self.assertIsNone(folder)
        self.assertEqual(1, len(errors))
        self.assertIn("Lizard_C.py: the download does not match the manifest", errors[0])
        self.assertEqual(["Lizard_A.py", "Lizard_B.py", "Lizard_Updater.py", "trnlizard_manifest.json"], self.cached())
        self.assertEqual("a = 1\n", UPDATER.readScript(os.path.join(self.folder, "Lizard_A.py")).replace("\r\n", "\n"))

    def test_failed_commit_lookup_falls_back_to_the_ref(self):
        for status in (403, 429, None, 404):
            self.github.calls = []
            self.github.fail("api.github.com", status)
            folder, log, errors = self.sync()
            self.assertEqual(self.folder, folder, status)
            self.assertEqual([], errors)
            self.assertTrue(any(line.startswith("Note: the commit of main could not be looked up") and "few minutes" in line
                                for line in log), status)
            self.assertFalse(any(line.startswith("Commit:") for line in log))
            self.assertTrue(all("/r/main/" in url for url, _ in self.github.calls[1:]))
            self.assertEqual(1, len([url for url, _ in self.github.calls if "api.github.com" in url]))   # never retried

    def test_a_commit_ref_needs_no_lookup(self):
        self.github.manifest_override = None
        folder, log, errors = self.sync(ref=SHA)
        self.assertEqual([], errors)
        self.assertFalse(any("api.github.com" in url for url, _ in self.github.calls))
        self.assertIn("Commit: " + SHA, log)
        self.assertTrue(folder.endswith("o_r_" + SHA))

    def test_rate_limited_downloads_are_retried_with_backoff(self):
        self.github.fail("trnlizard_manifest.json", 429, 503)
        self.github.fail("Lizard_B.py", 502)
        folder, log, errors = self.sync()
        self.assertEqual([], errors)
        self.assertEqual(self.folder, folder)
        self.assertEqual([mock.call(1.0), mock.call(2.0), mock.call(1.0)], self.sleep.call_args_list)
        self.assertEqual(3, len([line for line in log if line.startswith("Note: HTTP")]))

    def test_retry_after_is_honoured_and_the_wait_is_capped(self):
        self.github.failures["trnlizard_manifest.json"] = [UPDATER.SourceError("limited", 429, 3.0)]
        folder, log, errors = self.sync()
        self.assertEqual([], errors)
        self.assertEqual([mock.call(3.0)], self.sleep.call_args_list)
        self.sleep.reset_mock()
        self.github.failures["trnlizard_manifest.json"] = [UPDATER.SourceError("limited", 429, 60.0)]
        folder, log, errors = self.sync()   # too long: no wait, the complete cache is used
        self.assertEqual([], self.sleep.call_args_list)
        self.assertEqual(self.folder, folder)

    def test_the_wait_cap_holds_for_the_whole_update(self):
        self.github.failures["trnlizard_manifest.json"] = [UPDATER.SourceError("limited", 429, 6.0)]
        self.github.failures["Lizard_A.py"] = [UPDATER.SourceError(
            UPDATER.describeHttpFailure("Lizard_A.py", 429, "x"), 429, 6.0)]
        folder, log, errors = self.sync()
        self.assertEqual([mock.call(6.0)], self.sleep.call_args_list)   # 6 + 6 s would exceed MAX_RETRY_WAIT_S
        self.assertIsNone(folder)
        self.assertIn("GitHub rate limit (HTTP 429)", errors[0])

    def test_rate_limit_without_cache_is_a_clear_error(self):
        self.github.fail("trnlizard_manifest.json", 429, 429, 429)
        folder, log, errors = self.sync()
        self.assertIsNone(folder)
        self.assertEqual(1, len(errors))
        self.assertIn("GitHub rate limit (HTTP 429) - try again later or set source to a local folder", errors[0])
        self.assertIn("No complete cached copy", errors[0])
        self.assertEqual(2, self.sleep.call_count)

    def test_no_connection_uses_a_complete_cache(self):
        self.sync()
        for fragment, statuses in (("trnlizard_manifest.json", (None,)), ("trnlizard_manifest.json", (429, 429, 429)),
                                   ("trnlizard_manifest.json", (500,))):
            self.github.fail(fragment, *statuses)
            folder, log, errors = self.sync()
            self.assertEqual(self.folder, folder, statuses)
            self.assertEqual([], errors)
            warnings = [line for line in log if line.startswith("WARNING:")]
            self.assertEqual(1, len(warnings))
            self.assertIn("Using the cached copy (manifest generated 2026-10-21T10:00:00Z)", warnings[0])

    def test_failed_file_download_keeps_the_old_cache(self):
        self.sync()
        self.github.scripts["Lizard_A.py"] = "a = 2\n"
        self.github.scripts["Lizard_C.py"] = "c = 1\n"
        self.github.fail("Lizard_C.py", None)
        folder, log, errors = self.sync()
        self.assertEqual(self.folder, folder)   # the old complete copy, nothing half updated
        self.assertEqual(["Lizard_A.py", "Lizard_B.py", "Lizard_Updater.py", "trnlizard_manifest.json"], self.cached())
        self.assertEqual("a = 1\n", UPDATER.readScript(os.path.join(self.folder, "Lizard_A.py")).replace("\r\n", "\n"))
        self.assertTrue(any(line.startswith("WARNING:") for line in log))

    def test_incomplete_cache_is_not_used(self):
        self.sync()
        os.remove(os.path.join(self.folder, "Lizard_A.py"))
        self.github.fail("trnlizard_manifest.json", None)
        folder, log, errors = self.sync()
        self.assertIsNone(folder)
        self.assertIn("No complete cached copy", errors[0])

    def test_not_found_is_an_error_even_with_a_cache(self):
        self.sync()
        self.github.fail("api.github.com", 404)
        self.github.fail("trnlizard_manifest.json", 404)
        folder, log, errors = self.sync()
        self.assertIsNone(folder)
        self.assertIn("repository or ref not found, or the repository is private", errors[0])
        self.assertNotIn("cached copy", errors[0])

    def test_a_missing_manifest_of_an_existing_commit_says_so(self):
        self.github.fail("trnlizard_manifest.json", 404)
        folder, log, errors = self.sync()
        self.assertIsNone(folder)
        for fragment in ("o/r has no trnlizard_manifest.json at main (commit 0123456789ab)", "build_manifest.py"):
            self.assertIn(fragment, errors[0])

    def test_invalid_manifest_is_an_error(self):
        self.github.manifest_override = json.dumps({"format": 9, "files": {}})
        folder, log, errors = self.sync()
        self.assertIsNone(folder)
        self.assertIn("Invalid manifest", errors[0])
        self.assertIn("newer than this updater", errors[0])
        self.assertFalse(os.path.exists(self.folder))


class FileAndSourceGlueTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)

    def test_write_text_file_replaces_and_keeps_line_endings(self):
        path = os.path.join(self.root, "x.py")
        UPDATER.writeTextFile(path, "a\r\nb\n")
        UPDATER.writeTextFile(path, "c\r\n\u00e4\n")
        with open(path, "rb") as handle:
            self.assertEqual("c\r\n\u00e4\n".encode("utf-8"), handle.read())
        self.assertEqual(["x.py"], os.listdir(self.root))

    def test_write_text_file_without_os_replace(self):
        # IronPython 2.7: no os.replace, and os.rename does not overwrite on Windows
        def rename(src, dst):
            if os.path.exists(dst):
                raise OSError("exists")
            os.rename(src, dst)
        fake_os = SimpleNamespace(path=os.path, remove=os.remove, rename=rename)
        path = os.path.join(self.root, "x.py")
        with mock.patch.object(UPDATER, "os", fake_os):
            UPDATER.writeTextFile(path, "one\n")
            UPDATER.writeTextFile(path, "two\n")
        with open(path, encoding="utf-8") as handle:
            self.assertEqual("two\n", handle.read())
        self.assertEqual(["x.py"], os.listdir(self.root))

    def test_cache_root_falls_back_to_appdata(self):
        with mock.patch.dict(os.environ, {"APPDATA": self.root}):
            self.assertEqual(os.path.join(self.root, "TRNLizard", "source"), UPDATER.sourceCacheRoot())
        with mock.patch.object(UPDATER.Grasshopper, "Folders", SimpleNamespace(AppDataFolder="/gh"), create=True):
            self.assertEqual(os.path.join("/gh", "TRNLizard", "source"), UPDATER.sourceCacheRoot())

    def test_resolve_source(self):
        log, errors = [], []
        self.assertEqual(self.root, UPDATER.resolveSource(self.root, log, errors))
        self.assertEqual([], errors)
        self.assertIsNone(UPDATER.resolveSource(os.path.join(self.root, "missing"), log, errors))
        self.assertIn("Invalid source folder path", errors[-1])
        self.assertIsNone(UPDATER.resolveSource("https://gitlab.com/o/r", log, errors))
        self.assertIn("only GitHub", errors[-1])
        github = FakeGitHub({"Lizard_A.py": "a = 1\n"})
        log, errors = [], []
        with mock.patch.object(UPDATER, "httpGetText", github), \
                mock.patch.object(UPDATER, "sourceCacheRoot", lambda: self.root):
            folder = UPDATER.resolveSource("https://github.com/o/r", log, errors)
        self.assertEqual([], errors)
        self.assertEqual(os.path.join(self.root, "o_r_main"), folder)
        self.assertEqual(["Lizard_A"], list(UPDATER.findScripts(folder, [])))

    def test_run_updater_reports_a_bad_source(self):
        component = SimpleNamespace(InstanceGuid="guid-1")
        with mock.patch.object(UPDATER, "ghenv", SimpleNamespace(Component=component), create=True):
            log, updated, skipped, errors = UPDATER.runUpdater("https://gitlab.com/o/r", True)
            self.assertEqual("=== TRNLizard Updater Started ===", log[0])
            self.assertEqual(1, len(errors))
            self.assertIn("only GitHub", errors[0])
            log, updated, skipped, errors = UPDATER.runUpdater(None, False)
            self.assertEqual(["Set runUpdate to True to execute the updater."], log)


if __name__ == "__main__":
    unittest.main()
