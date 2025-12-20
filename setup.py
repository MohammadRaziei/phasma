import platform, os
from pathlib import Path
from setuptools import setup, find_namespace_packages
from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
import sys
import logging

SRC_PATH = Path(__file__).parent / "src"
sys.path.append(SRC_PATH.as_posix())

from phasma.driver.download import download_driver, setup_logging


setup_logging()

logger = logging.getLogger("setup")


class bdist_wheel(_bdist_wheel):
    def detect_platform(self):
        os_name = os.getenv("TARGET_OS")
        arch = os.getenv("TARGET_ARCH")

        if not os_name or not arch:

            os_name = platform.system().lower()
            machine = platform.machine().lower()
            arch = "64bit"

            if os_name == "linux":
                arch = "64bit" if "64" in machine else "32bit"

        return os_name, arch


    def run(self):
        os_name, arch = self.detect_platform()
        logger.info(f"Downloading PhantomJS for {os_name} {arch}")
        dest = SRC_PATH / "phasma" / "driver"
        success = download_driver(dest=dest, os_name=os_name, arch=arch)
        if not success:
            logger.error("Download Failed")
            raise RuntimeError("Download Failed")

        super().run()

    def finalize_options(self):
        super().finalize_options()
        os_name, arch = self.detect_platform()
        if os_name == "linux":
            self.plat_name =  "manylinux_2_17_x86_64" if arch == "64bit" else "manylinux_2_17_i686"
        elif os_name == "windows":
            self.plat_name = "win_amd64"
        elif os_name == "darwin":
            self.plat_name = "macosx_10_9_x86_64"

        self.plat_name_supplied = True


if __name__ == "__main__":
    setup(
        packages=find_namespace_packages(where="src"),
        package_dir={"": "src"},
        include_package_data=True,
        package_data={
            "phasma.driver.phantomjs": ["*", "**/*"],
        },
        options={
            "egg_info": {"egg_base": "."},
        },
        platforms=["Linux", "Windows", "macOS"],
        cmdclass={
            "bdist_wheel": bdist_wheel,
        },
    )
