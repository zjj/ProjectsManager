from setuptools import find_packages, setup

setup(
    name='ProjectsManager',
    author = 'zhongjj',
    author_email='79492390@qq.com',
    version='0.1',
    zip_safe=True,
    packages=find_packages(exclude=['*.tests*']),
    entry_points = """
        [trac.plugins]
        projectsmanager = projectsmanager
    """,
    description = 'Projects management plugin for Trac',
    packages=['projectsmanager'],
    package_data={'projectsmanager': ['templates/*.html',
                                      'templates/*.txt']},
)

