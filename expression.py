import numpy as np

# ฟังก์ชัน expression สำเร็จรูป ที่รับ pd.Series 'x' แล้ว return pd.Series ใหม่
def scale(value, in_min, in_max, out_min, out_max):
    """Scale a value from one range to another."""
    if in_max == in_min:
        raise ValueError("Input range cannot be zero.")
    return (value - in_min) / (in_max - in_min) * (out_max - out_min) + out_min

def identity(x):
    return x

def log_plus_one(x):
    return np.log(x + 1)

def square(x):
    return x ** 2

def sqrt(x):
    return np.sqrt(x)

def normalize(x):
    return (x - x.min()) / (x.max() - x.min())

def scale_throttle(x):
    return  (1000 - (((x + 100) / 200) * 1000)) + 1000

def left_elevetor(x):
    """คำนวณตำแหน่ง left elevator จากค่า input x (รองรับทั้ง scalar และ Series)"""
    x = np.asarray(x)
    rad = scale(x, 100, -100, -0.174533, 0.174533)
    rad = np.clip(rad, -0.349066, 0.349066)

    # เตรียม array สำหรับผลลัพธ์
    result = np.full_like(rad, np.nan, dtype=np.float64)

    segments = [
        (-0.349066, -0.261799, -756.304290, 1512.0),
        (-0.261799, -0.174533, -779.222601, 1506.0),
        (-0.174533, -0.087266, -687.549354, 1522.0),
        (-0.087266,  0.0,       -939.650784, 1500.0),
        ( 0.0,       0.087266, -870.895841, 1498.0),
        ( 0.087266,  0.174533, -825.059225, 1496.0),
        ( 0.174533,  0.261799, -1008.405719, 1528.0),
        ( 0.261799,  0.349066, -905.273316, 1501.0),
    ]

    for x0, x1, m, b in segments:
        mask = (rad >= x0) & (rad <= x1)
        result[mask] = m * rad[mask] + b

    return result

# เก็บเป็น dict สำหรับโหลดใน app.py
expressions = {
    "None": identity,
    "Logarithm (log(x+1))": log_plus_one,
    "Square (x^2)": square,
    "Square root (sqrt(x))": sqrt,
    "Normalize ((x - min) / (max - min))": normalize,
    "Scale Throttle(x)": scale_throttle,
    "scale((x - in_min) / (in_max - in_min) * (out_max - out_min) + out_min)" : scale,
    "Left Elevon(x)": left_elevetor,
}
