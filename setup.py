import platform, os
from setuptools import setup, find_namespace_packages
from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
import logging

from phantomjs_driver.driver.download import download_driver, setup_logging

logger = logging.getLogger("setup")

setup_logging(logger)

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
        download_driver(os_name=os_name, arch=arch)

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
            "phantomjs_driver.driver.phantomjs": ["*", "**/*"],
        },
        options={
            "egg_info": {"egg_base": "."},
        },
        platforms=["Linux", "Windows", "macOS"],
        cmdclass={
            "bdist_wheel": bdist_wheel,
        },
    )
