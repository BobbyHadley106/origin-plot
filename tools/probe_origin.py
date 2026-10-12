"""
Origin 连通性探针 —— 在装有 Origin 的 Windows 本机上运行。

    pip install originpro
    python tools/probe_origin.py            # 附着到正在运行的 Origin 并画一张测试图
    python tools/probe_origin.py --no-plot  # 只测连接，不在当前项目里新建任何东西

脚本结束时只 detach（释放连接），不会关闭你的 Origin 窗口。
--no-plot 以外的模式会在当前项目里新建 "ProbeData" 工作簿和 "ProbeGraph" 图，可手动删除。
"""
import os
import platform
import struct
import sys
import tempfile
import traceback


def step(title, func):
    print(f"\n[{title}]")
    try:
        result = func()
        print(f"  OK  {result if result is not None else ''}")
        return True
    except Exception as e:  # noqa: BLE001 - 探针需要报告所有异常
        print(f"  FAIL  {type(e).__name__}: {e}")
        traceback.print_exc(limit=3)
        return False


def main():
    no_plot = "--no-plot" in sys.argv

    print("Python  :", sys.version.split()[0], f"({struct.calcsize('P') * 8}-bit)")
    print("System  :", platform.platform())
    if os.name != "nt":
        print("FAIL: originpro 只支持 Windows。")
        return 1

    try:
        import originpro as op
    except ImportError as e:
        print(f"FAIL: 无法导入 originpro（{e}）。请先运行 pip install originpro")
        return 1

    try:
        from importlib.metadata import version
        print("originpro:", version("originpro"), "| OriginExt:", version("OriginExt"))
    except Exception:  # noqa: BLE001
        pass

    results = {}
    results["attach"] = step("1. 附着到正在运行的 Origin (op.attach)", lambda: op.attach())
    if not results["attach"]:
        print("\n结论：无法附着。请确认 Origin 已打开；若仍失败，可能是该版本未开放 COM 自动化接口。")
        return 2

    results["version"] = step("2. 读取 Origin 版本 (@V)", lambda: f"@V = {op.org_ver()}")
    results["visible"] = step("3. 读取窗口可见性 (@VIS)", lambda: f"visible = {op.get_show()}")
    results["labtalk"] = step(
        "4. 执行 LabTalk",
        lambda: (op.lt_exec("double __probe = 1 + 1;"), f"1+1 = {op.lt_float('__probe')}")[1],
    )

    if not no_plot:
        png = os.path.join(tempfile.gettempdir(), "origin_probe.png")

        def plot():
            wks = op.new_sheet(lname="ProbeData")
            wks.from_list(0, [1, 2, 3, 4, 5], lname="X")
            wks.from_list(1, [1, 4, 9, 16, 25], lname="Y")
            gp = op.new_graph(lname="ProbeGraph", template="line")
            gl = gp[0]
            gl.add_plot(wks, coly=1, colx=0)
            gl.rescale()
            out = gp.save_fig(png, type="png", width=800)
            if not out or not os.path.exists(png):
                raise RuntimeError(f"save_fig 未生成文件（返回值：{out!r}）")
            return f"已导出 {out}"

        results["plot"] = step("5. 新建工作表 + 折线图 + 导出 PNG", plot)

    step("6. 断开连接 (op.detach，不关闭 Origin)", lambda: op.detach())

    print("\n==== 汇总 ====")
    for k, v in results.items():
        print(f"  {k:8s} {'OK' if v else 'FAIL'}")
    return 0 if all(results.values()) else 3


if __name__ == "__main__":
    sys.exit(main())
