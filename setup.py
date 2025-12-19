from setuptools import setup, find_namespace_packages

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
    )
