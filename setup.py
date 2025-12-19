from setuptools import setup, find_namespace_packages
from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
import platform


class bdist_wheel(_bdist_wheel):
    def finalize_options(self):
        super().finalize_options()

        system = platform.system().lower()
        machine = platform.machine().lower()

        self.plat_name_supplied = True
        if system == "windows":
            self.plat_name = "win_amd64"

        elif system == "darwin":
            self.plat_name = "macosx_10_9_x86_64"

        elif system == "linux":
            if machine in ("x86_64", "amd64"):
                self.plat_name = "manylinux_2_17_x86_64"
            else:
                self.plat_name = "manylinux_2_17_i686"

if __name__ == "__main__":
    setup(
        packages=find_namespace_packages(where="src"),
        package_dir={"": "src"},
        include_package_data=True,
        package_data={
            "phantomjs_driver.driver": ["*", "**/*"],
        },
        options={
            "egg_info": {"egg_base": "."},
        },
        platforms=["Linux", "Windows", "macOS"],
        cmdclass={
            "bdist_wheel": bdist_wheel,
        },
    )
