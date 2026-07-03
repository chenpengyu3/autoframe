from autoframe.plugins.base import TestModule


class FilesTestModule(TestModule):
    @property
    def name(self) -> str:
        return "files"

    @property
    def description(self) -> str:
        return "File endpoint testing - upload, download, binary response contracts"
