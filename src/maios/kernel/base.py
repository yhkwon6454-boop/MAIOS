from abc import ABC, abstractmethod


class BaseKernel(ABC):
    """모든 Kernel의 공통 인터페이스"""

    @abstractmethod
    def initialize(self):
        pass

    @abstractmethod
    def execute(self, packet):
        pass

    @abstractmethod
    def validate(self, result):
        pass

    @abstractmethod
    def shutdown(self):
        pass