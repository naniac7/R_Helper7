from setuptools import setup, find_namespace_packages

# src2와 src 폴더 모두 인식 (전환 기간 동안 병행)
# find_namespace_packages()는 __init__.py 없이도 패키지를 자동 탐색
setup(name="R_Helper7", packages=find_namespace_packages())
