from setuptools import setup, find_namespace_packages
from wheel.bdist_wheel import bdist_wheel


class BinaryWheel(bdist_wheel):
    def finalize_options(self):
        super().finalize_options()
        self.root_is_pure = False   

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
        classifiers=[
            "Programming Language :: Python :: 3",
            "Operating System :: POSIX :: Linux",
            "Operating System :: MacOS :: MacOS X",
            "Operating System :: Microsoft :: Windows",
        ],
        platforms=["Linux", "Windows", "macOS"],
    )
