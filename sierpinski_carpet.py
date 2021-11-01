# reference ==>
# https://zh.wikipedia.org/wiki/%E8%B0%A2%E5%B0%94%E5%AE%BE%E6%96%AF%E5%9F%BA%E5%9C%B0%E6%AF%AF
import taichi as ti
import os

ti.init(arch=ti.cuda)

deepth = 5
res_x = 3**deepth
res_y = 3**deepth
pixels_1 = ti.Vector.field(3, ti.f32, shape=(res_x, res_y))
pixels_2 = ti.Vector.field(3, ti.f32, shape=(res_x, res_y))
flags_1 = ti.field(ti.i32, shape=(res_x, res_y))
flags_2 = ti.field(ti.i32, shape=(res_x, res_y))


@ti.func
def fill(x, y, W, H, deepth):
    c = 0
    for i in range(deepth):
        if x < 1 or W < 1 or H < 1:
            break
        x_ = (3 * x) // W
        y_ = (3 * y) // H
        if x_ == 1 and y_ == 1:
            c = 1 + i
            break
        x -= (x_ * W) // 3
        y -= (y_ * H) // 3
        W = W // 3
        H = H // 3
    return c


@ti.func
def zoom_in(t: ti.f32):
    scale = ti.pow(1 / 3, (t % 120) / 120)
    for i, j in pixels_2:
        flags_2[i, j] = flags_1[i, j]
        if scale < 1:
            i_ = ti.floor(scale * i)
            j_ = ti.floor(scale * j)
            flags_2[i, j] = flags_1[i_, j_]


@ti.kernel
def render(t: ti.f32):
    # draw something on your canvas
    white = ti.Vector([1.0, 1.0, 1.0])
    black = ti.Vector([0.0, 0.0, 0.0])
    for i, j in flags_1:
        flags_1[i, j] = fill(i, j, res_x, res_y, deepth)
        pixels_1[i, j] = white
        pixels_2[i, j] = white
    zoom_in(t)
    for i, j in flags_2:
        if flags_2[i, j] > 0:
            pixels_2[i, j] = black
        if flags_2[i, j] == deepth:
            gray = 2 - ti.pow(2, (t % 120) / 120)
            pixels_2[i, j] = ti.Vector([gray, gray, gray])




if __name__ == '__main__':
    gui = ti.GUI("Canvas", res=(res_x, res_y))
    if not os.path.exists(f'./carpet_results'):
        os.mkdir('./carpet_results')
    for i in range(120):
        t = i * 1.0
        render(t)
        gui.set_image(pixels_2)
        filename = f'./carpet_results/frame_{i:05d}.png'  # create filename with suffix png
        print(f'Frame {i} is recorded in {filename}')
        gui.show(filename)  # export and show in GUI
