# https://www.cnblogs.com/heymonkey/p/11727939.html

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException
from PIL import Image
from io import BytesIO
from time import sleep
import random

"""
info:
author:CriseLYJ
github:https://github.com/CriseLYJ/
update_time:2019-3-7
"""


class BiliBili():
    """
    登陆B站, 处理验证码
    电脑的缩放比例需要为100%, 否则验证码图片的获取会出现问题
    """

    def __init__(self, username, password):
        """
        初始化
        """
        options = webdriver.ChromeOptions()
        # 设置为开发者模式，避免被识别
        options.add_experimental_option('excludeSwitches',
                                        ['enable-automation'])
        self.browser = webdriver.Chrome(options=options)
        self.url = 'https://passport.bilibili.com/login'
        self.browser.get(self.url)
        self.wait = WebDriverWait(self.browser, 5, 0.2)
        self.username = username
        self.password = password

    def get_button(self):
        """
        获取滑动块, 并且返回
        :return: button
        """
        button = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'geetest_slider_button')))
        return button

    def get_screenshot(self, left, top, right, bottom, name):
        """
        获取网页两次截图:
            1. 鼠标悬停于button的截图
            2. 鼠标点击button后的截图
        :param button: 滑动块
        :return: 两次截图的结果
        """
        # 获取全屏截图
        screenshot = self.browser.get_screenshot_as_png()
        # 用pil的Image转换成Pil截图
        screenshot = Image.open(BytesIO(screenshot))
        # 获取完整图片的截图
        captcha = screenshot.crop((left, top, right, bottom))
        captcha.save(name)
        return captcha

    def get_position(self):
        """
        获取验证码图片的位置
        :return: 位置的四个点参数
        """
        # 等待出现
        sleep(2)
        img = self.browser.find_element_by_css_selector('.geetest_canvas_img.geetest_absolute')
        location = img.location
        print("图片的位置：", location)
        size = img.size
        top, bottom, left, right = location['y'], location['y'] + size['height'], location['x'], \
                                   location['x'] + size['width']
        print('验证码截图坐标', left, top, right, bottom)
        return top, bottom, left, right

    def get_geetest_image(self, name1='captcha1.png', name2='captcha2.png'):
        """
        获取两次验证码的截图:
            1. 鼠标悬停于button的截图
            2. 鼠标点击button后的截图
        :param button: 滑动块
        :param name1: 原始验证码保存的名字
        :param name2: 缺块验证码保存的名字
        :return: 两次验证码截图的结果
        """
        # 获取验证码 左上角 右下角 坐标
        top, bottom, left, right = self.get_position()

        # 执行js改变css样式，显示没有缺口的图
        self.browser.execute_script("document.querySelectorAll('canvas')[3].style=''")
        captcha1 = self.get_screenshot(left, top, right, bottom, name1)
        sleep(1)
        # 执行js改变css样式，显示有缺口的图
        self.browser.execute_script("document.querySelectorAll('canvas')[3].style='display: none;'")
        captcha2 = self.get_screenshot(left, top, right, bottom, name2)
        return (captcha1, captcha2)

    def login(self):
        """
        打开浏览器,并且输入账号密码
        :return: None
        """
        try:
            self.browser.maximize_window()
        except Exception as e:
            pass

        self.browser.get(self.url)

        username = self.wait.until(EC.element_to_be_clickable((By.ID, 'login-username')))
        password = self.wait.until(EC.element_to_be_clickable((By.ID, 'login-passwd')))
        sleep(1)
        username.send_keys(self.username)
        sleep(1)
        password.send_keys(self.password)

        loginsubmit = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'btn-login')))
        loginsubmit.click()

        # 校验验证码
        self.crack()

    def is_pixel_equal(self, img1, img2, x, y):
        """
        判断两个像素是否相同
        :param img1: 原始验证码
        :param img2: 缺块验证码
        :param x: 像素点的x坐标
        :param y: 像素点的y坐标
        :return: 像素是否相同
        """
        pixel1 = img1.load()[x-1, y]
        pixel2 = img2.load()[x-1, y]
        threshold = 100
        if abs(pixel1[0] - pixel2[0]) < threshold and abs(pixel1[1] - pixel2[1]) < threshold and abs(
                pixel1[2] - pixel2[2]) < threshold:
            return True
        else:
            return False

    def get_gap(self, img1, img2):
        """
        获取缺口偏移量
        :param img1: 原始验证码
        :param img2: 缺块验证码
        :return: 第二个缺块的左侧的x坐标
        """
        left = 60  # 大致忽略掉第一个缺块
        # image size 0表示宽 1表示高
        for i in range(left, img1.size[0]):
            for j in range(img1.size[1]):
                if not self.is_pixel_equal(img1, img2, i, j):
                    left = i
                    return left - 7
        return left - 7

    def get_track(self, distance):
        """
        获取滑块移动轨迹的列表
        :param distance: 第二个缺块的左侧的x坐标
        :return: 滑块移动轨迹列表
        """
        # 移动轨迹
        track = []
        # 当前位置
        current = 0
        # 减速阈值
        mid = distance * 2 / 3
        # 间隔时间
        t = 0.2
        v = 0
        distance += 10  # 使滑块划过目标地点, 然后回退
        while current < distance:
            if current < mid:
                a = random.randint(1, 3)
            else:
                a = - random.randint(3, 5)
            v0 = v
            # 当前速度
            v = v0 + a * t
            # 移动距离
            move = v0 * t + 1 / 2 * a * t * t
            # 当前位置
            current += move
            #
            track.append(round(move))
        for i in range(2):
            track.append(-random.randint(2, 3))
        for i in range(2):
            track.append(-random.randint(1, 4))
        return track

    def move_button(self, button, track):
        """
        将滑块拖动到指定位置
        :param button: 滑动块
        :param track: 滑块运动轨迹列表
        :return: None
        """
        ActionChains(self.browser).click_and_hold(button).perform()
        for i in track:
            ActionChains(self.browser).move_by_offset(xoffset=i, yoffset=0).perform()
            sleep(0.0005)
        sleep(0.5)
        print('release')
        ActionChains(self.browser).release().perform()
        sleep(5)

    def handleException(self, left):
        try:
            error = self.browser.find_element_by_css_selector('.geetest_panel_error_content')
            if error:
                error.click()
                sleep(5)
                self.crack()
        except ElementNotInteractableException as e:
            # 报这个异常说明验证码没对上
            sleep(2)
            self.move(left)

    def move(self, left):
        button = self.get_button()
        # 如果尝试登陆失败, 则重新验证, 最多三次
        times = 0
        while times < 3:
            track = self.get_track(left)
            self.move_button(button, track)
            try:
                success = self.browser.find_element_by_xpath("//div[contains(text(), '账号安全评分')]")
                print(success)

                # 获取cookies
                cookies = self.browser.get_cookies()
                print(cookies)
                cookie_dict = {}
                for cookie in cookies:
                    cookie_dict[cookie['name']] = cookie['value']
                print(cookie_dict)
            except NoSuchElementException as e:
                self.handleException(left)
            except TimeoutException as e:
                times += 1
                print('fail')
            else:
                print('success')
                self.browser.close()
                return None

    def crack(self):
        """
        串接整个流程:
            1. 获取滑动块
            2. 获取两张验证码图片
            3. 获取滑块移动轨迹
            4. 将滑块拖动至指定位置
        :return:
        """
        captcha = self.get_geetest_image()
        left = self.get_gap(captcha[0], captcha[1])
        print(left)
        self.move(left)


if __name__ == '__main__':
    ACCOUNT = input('请输入您的账号:')
    PASSWORD = input('请输入您的密码:')
    test = BiliBili(ACCOUNT, PASSWORD)  # 输入账号和密码
    test.login()
