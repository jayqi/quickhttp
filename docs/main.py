from pathlib import Path
import re


def define_env(env):
    @env.macro
    def include_readme():
        content = (Path(__file__).parent.parent / "README.md").read_text()

        install_tabs_content = (
            Path(__file__).parent / "partials" / "installation_tabs.md"
        ).read_text()
        install_pattern = re.compile(
            r"<!-- Installation start -->(.*?)<!-- Installation end -->", re.DOTALL
        )

        content = install_pattern.sub(install_tabs_content, content)

        return content

    @env.macro
    def include_changelog():
        content = (Path(__file__).parent.parent / "CHANGELOG.md").read_text()
        return content
