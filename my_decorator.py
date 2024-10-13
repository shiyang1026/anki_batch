import time

def time_cal(func):
    """
    装饰器：计算函数运行时间
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"图片导入Anki成功, {func.__name__} 总用时: {end_time - start_time:.2f} 秒")
        return result
    return wrapper