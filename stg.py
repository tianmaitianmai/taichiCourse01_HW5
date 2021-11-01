import taichi as ti
import handy_shader_functions as hsf
import os

ti.init(arch=ti.cuda)

res_x = 512
res_y = 512

pixels = ti.Vector.field(3, ti.f32, shape=(res_x, res_y))

PI = 3.1415926
twoPI = 2.0 * PI
white = ti.Vector([1.0, 1.0, 1.0])
black = ti.Vector([0.0, 0.0, 0.0])
red = ti.Vector([1.0, 0.0, 0.0])
green = ti.Vector([0.0, 1.0, 0.0])
blue = ti.Vector([0.0, 0.0, 1.0])


@ti.func
def rotating_matrix(theta):
    sin_ = ti.sin(theta)
    cos_ = ti.cos(theta)
    m = ti.Matrix([[cos_, sin_], [-sin_, cos_]])
    return m


@ti.func
def circle(pos, center, radius, blur):
    r = (pos - center).norm()
    t = 0.0
    if blur > 1.0: blur = 1.0
    if blur <= 0.0:
        t = 1.0 - hsf.step(1.0, r / radius)
    else:
        t = hsf.smoothstep(1.0, 1.0 - blur, r / radius)
    return t


@ti.func
def color_ring(x):
    c = ti.Vector([0.0, 0.0, 0.0])
    if x >= 0 and x < 1 / 3:
        c[0] = 1 - 3 * x
        c[1] = 3 * x
    elif x < 2 / 3:
        c[1] = 2 - 3 * x
        c[2] = 3 * x - 1
    elif x <= 1:
        c[2] = 3 - 3 * x
        c[0] = 3 * x - 2
    return c


@ti.func
def quad_func(x, factor):
    return factor[0] * x**2 + factor[1] * x + factor[2]


@ti.func
def quad_func_diff(x, factor):
    return 2 * factor[0] * x + factor[1]


@ti.func
def bullet_template_1(t, pos, shift, R_quad_factor, accel_stop_t,
                      expand_factor, expand_stop_t, theta_0, omega, num,
                      t_shift_quad_factor):
    mask = 0
    t_0 = t
    for k in range(num):
        t = t_0
        t = t - quad_func(k, t_shift_quad_factor)
        if t >= 0:
            R = quad_func(t, R_quad_factor)
            if t >= accel_stop_t:
                R = 2 * R_quad_factor[0] * accel_stop_t * (
                    t - accel_stop_t) + quad_func(accel_stop_t, R_quad_factor)
            u_k = R * ti.cos(k * twoPI / num + theta_0)
            v_k = R * ti.sin(k * twoPI / num + theta_0)
            u_k = (u_k + 1.5) % 3.0 - 1.5
            v_k = (v_k + 1.5) % 3.0 - 1.5
            ma = rotating_matrix((omega * t) % twoPI)
            centroid_k = ti.Vector([u_k, v_k])
            centroid_k = ma @ centroid_k
            centroid_k += shift
            rho_k = 0.005 + expand_factor * ti.min(t, expand_stop_t)
            blur_k = 0.5
            mask += circle(pos, centroid_k, rho_k, blur_k)
    return mask


@ti.kernel
def render(t: ti.f32):
    for i, j in pixels:
        pixels[i, j] = black
        u = 2.0 * float(i) / res_x - 1.0
        v = 2.0 * float(j) / res_y - 1.0
        nn = 12

        for k in range(nn):
            R = 0.2
            c = color_ring(float(k) / nn)
            shift_u = R * ti.cos(k * twoPI / nn)
            shift_v = R * ti.sin(k * twoPI / nn)
            R_quad_factor = ti.Vector([0.01, 0.0, 0.0])
            accel_stop_t = 10
            expand_factor = 0.005
            expand_stop_t = 10
            theta_0 = 0.0
            omega = 0.2
            num = 18
            t_shift_quad_factor = ti.Vector([0.0, 0.0, 3.0])
            mask = bullet_template_1(t, ti.Vector([u, v]),
                                     ti.Vector([shift_u, shift_v]),
                                     R_quad_factor, accel_stop_t,
                                     expand_factor, expand_stop_t, theta_0,
                                     omega, num, t_shift_quad_factor)
            pixels[i, j] += c * mask

        nn = 24
        for k in range(nn):
            R = 0.0
            c = color_ring(float(k) / nn)
            shift_u = R * ti.cos(k * twoPI / nn)
            shift_v = R * ti.sin(k * twoPI / nn)
            R_quad_factor = ti.Vector([0.02, 0.0, 0.0])
            accel_stop_t = 10
            expand_factor = 0.01
            expand_stop_t = 10
            theta_0 = twoPI * k / nn
            omega = 0.5
            num = 12
            t_shift_quad_factor = ti.Vector([0.03, 0.0, 0.0])
            mask = bullet_template_1(t, ti.Vector([u, v]),
                                     ti.Vector([shift_u, shift_v]),
                                     R_quad_factor, accel_stop_t,
                                     expand_factor, expand_stop_t, theta_0,
                                     omega, num, t_shift_quad_factor)
            pixels[i, j] += c * mask

        nn = 24
        for k in range(nn):
            R = 0.0
            c = color_ring(float(k) / nn)
            shift_u = R * ti.cos(k * twoPI / nn)
            shift_v = R * ti.sin(k * twoPI / nn)
            R_quad_factor = ti.Vector([0.04, 0.0, 0.0])
            accel_stop_t = 10
            expand_factor = 0.006
            expand_stop_t = 10
            theta_0 = twoPI * k / nn
            omega = -0.3
            num = 12
            t_shift_quad_factor = ti.Vector([0.01, 0.0, 1.0])
            mask = bullet_template_1(t, ti.Vector([u, v]),
                                     ti.Vector([shift_u, shift_v]),
                                     R_quad_factor, accel_stop_t,
                                     expand_factor, expand_stop_t, theta_0,
                                     omega, num, t_shift_quad_factor)
            pixels[i, j] += c * mask


if __name__ == '__main__':
    gui = ti.GUI('Canvas', res=(res_x, res_y))
    if not os.path.exists(f'./stg_results'):
        os.mkdir('./stg_results')
    for i in range(6000):
        t = i * 0.05
        render(t)
        gui.set_image(pixels)
        gui.show()
        #filename = f'./stg_results/frame_{i:05d}.png'  # create filename with suffix png
        #print(f'Frame {i} is recorded in {filename}')
        #gui.show(filename)  # export and show in GUI
