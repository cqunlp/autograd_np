from typing import List,NamedTuple,Callable,Optional,Union
import numpy as np

class Dependency(NamedTuple):
    tensor: 'Tensor'
    grad_fn: Callable[[np.ndarray],np.ndarray]

Arrayable = Union[float, list, np.ndarray]

def ensure_arry(arrayable: Arrayable) -> np.ndarray:
    if isinstance(arrayable, np.ndarray):
        return arrayable
    else:
        return np.array(arrayable)

class Tensor:
    def __init__(self,
                data: Arrayable,
                requires_grad: bool = False,
                depends_on: List[Dependency] = None
    ) -> None:
        self.data = ensure_arry(data)
        self.requires_grad = requires_grad
        self.depends_on = depends_on or []

        self.shape = self.data.shape
        self.grad : Optional['Tensor'] = None

        if self.requires_grad:
            self.zero_grad()
        

    def zero_grad(self) -> None:
        self.grad = Tensor(np.zeros_like(self.data))

    def __repr__(self) -> str:
        return f"Tensor({self.data}.requires_grad={self.requires_grad})"

    def sum(self) -> 'Tensor':
        # raise NotImplementedError
        return tensor_sum(self)
    def backward(self, grad: 'Tensor' = None ) -> None:
        assert self.requires_grad,"called backward on non-requires-grad tensor"

        if grad is None:
            if self.shape == ():
                grad = Tensor(1)
            else:
                raise RuntimeError("grad must specified for non-0-tensor")

        self.grad.data += grad.data

        for dependency in self.depends_on:
            backward_grad = dependency.grad_fn(grad.data)
            dependency.tensor.backward(Tensor(backward_grad))



def tensor_sum(t:Tensor) -> Tensor:
    """
    Takes a tensor and returns the 0-tensor
    that's the sum of all its elements.
    """
    data = t.data.sum()
    requires_grad = t.requires_grad
    if requires_grad:
        def grad_fn(grad: np.ndarray) -> np.ndarray:
            """
            grad is necessarily a 0-tensor, so each input element
            contributes that much
            """
            return grad * np.ones_like(t.data)

        depends_on = [Dependency(t,grad_fn)]
    else:
        depends_on = []
    
    return Tensor(data,
                requires_grad,
                depends_on
        )

def add(t1: Tensor, t2:Tensor) -> Tensor:

    data = t1.data + t2.data
    requires_grad = t1.requires_grad or t2.requires_grad

    depends_on: List[Dependency] = []

    if t1.requires_grad:
        def grad_fn1(grad: np.ndarray) -> np.ndarray:
            # Idea: [1,2,3] + [4,5,6] => [5,7,9]
            # Handle the broadcasting properly
            # Sum out added dims
            ndims_added = grad.ndim - t1.data.ndim
            for _ in range(ndims_added):
                grad = grad.sum(axis = 0)

            # Sum across broadcasted (but non-added dims)
            # (2,3) + (1,3) => (2,3) grad(2,3)

            for i, dim in enumerate(t1.shape):
                if dim == 1:
                    grad = grad.sum(axis=i, keepdims = True)

            return grad
        depends_on.append(Dependency(t1, grad_fn1))
    
    if t2.requires_grad:
        def grad_fn2(grad: np.ndarray) -> np.ndarray:
            ndims_added = grad.ndim - t2.data.ndim
            for _ in range(ndims_added):
                grad = grad.sum(axis = 0)
             # Sum across broadcasted (but non-added dims)
            # (2,3) + (1,3) => (2,3) grad(2,3)

            for i, dim in enumerate(t2.shape):
                if dim == 1:
                    grad = grad.sum(axis=i, keepdims = True)
                    
            
            return grad
        depends_on.append(Dependency(t2, grad_fn2))

    return Tensor(data,
        requires_grad,
        depends_on
    )

def mul(t1: Tensor, t2:Tensor) -> Tensor:
    """
    y = (a + eps) * b = a * b + (eps * b * dL/dy)
    gradient_y = 5
    have dL/dy
    dL/da = dL/dy * dy/da(b)
    """
    data = t1.data * t2.data
    requires_grad = t1.requires_grad or t2.requires_grad

    depends_on: List[Dependency] = []

    if t1.requires_grad:
        def grad_fn1(grad: np.ndarray) -> np.ndarray:
            grad = grad * t2.data

            ndims_added = grad.ndim - t1.data.ndim
            for _ in range(ndims_added):
                grad = grad.sum(axis = 0)

            for i, dim in enumerate(t1.shape):
                if dim == 1:
                    grad = grad.sum(axis=i, keepdims = True)

            return grad
        depends_on.append(Dependency(t1, grad_fn1))
    
    if t2.requires_grad:
        def grad_fn2(grad: np.ndarray) -> np.ndarray:
            grad = grad * t1.data
            ndims_added = grad.ndim - t2.data.ndim
            for _ in range(ndims_added):
                grad = grad.sum(axis = 0)

            for i, dim in enumerate(t2.shape):
                if dim == 1:
                    grad = grad.sum(axis=i, keepdims = True)
                    
            return grad
        depends_on.append(Dependency(t2, grad_fn2))

    return Tensor(data,
        requires_grad,
        depends_on
    )

def neg(t: Tensor) -> Tensor:
    data = -t.data
    requires_grad = t.requires_grad
    if requires_grad:
        depends_on = [Dependency(t, lambda x: -x)]
    else:
        depends_on = []
    return Tensor(data, requires_grad, depends_on)

def sub(t1: Tensor, t2: Tensor) -> Tensor:
    return add(t1, neg(t2))
