"""
Lizard_Log_Check
-

Args:
    Variant (object): Script input Folder.
        Access: item
        Required: True


Returns:
    output (str): summary of the log files of the variant (variant name, daylight preprocessing and thermal simulation status, with the error lines of trnRAD.log / <variant>.lst); the same text as the component message, for a Panel
        Access: item
"""

'''vhoang - 20161010 (Optimized for Large Files)
    Input: Variant (string containing path and variant info)
    Output: output (Specific message based on log files)'''
import os
import scriptcontext as sc
import Grasshopper.Kernel as gh

# 初始化组件参数
version = '2.3.1'
ghenv.Component.Name = "Lizard_Log_Check"
ghenv.Component.NickName = 'Log_Check'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "3 | Components"

w = gh.GH_RuntimeMessageLevel.Warning
err = gh.GH_RuntimeMessageLevel.Error

# 提取项目路径和变量名
dummy = Variant.split('\t')
if len(dummy) >= 4:
    variant_name = dummy[1]
    ProjectFolder = dummy[3]
else:
    variant_name = "Unknown"
    ProjectFolder = ""

# 使用列表作为缓冲区，避免在循环中频繁操作字符串和组件UI
message_buffer = ["Variant: %s\n" % variant_name]
print("Variant: %s\n " % variant_name)

def find_log(path, var_name):
    daylight_log_name = "trnRAD.log"
    thermal_log_name = "%s.lst" % var_name
    daylight_path = os.path.join(path, "Daylight")
    
    log_paths = ['', '']
    
    # 优化点 1：优先检查预期路径，避免对庞大项目文件夹进行不必要的 os.walk 递归
    direct_dl_path = os.path.join(daylight_path, daylight_log_name)
    if os.path.isfile(direct_dl_path):
        log_paths[0] = direct_dl_path
    else:
        for root, dirs, files in os.walk(daylight_path):
            if daylight_log_name in files:
                log_paths[0] = os.path.join(root, daylight_log_name)
                break
                
    direct_th_path = os.path.join(path, thermal_log_name)
    if os.path.isfile(direct_th_path):
        log_paths[1] = direct_th_path
    else:
        for root, dirs, files in os.walk(path):
            if thermal_log_name in files:
                log_paths[1] = os.path.join(root, thermal_log_name)
                break
                
    return log_paths

def scan_log_file(paths):
    daylight_log_path, thermal_log_path = paths
    
    # --- 扫描 Daylight 日志 ---
    if not daylight_log_path:
        msg = "You don't have Daylight Preprocessing log file. \nPlease run Daylight Preprocessing!\n"
        print(msg)
        message_buffer.append(msg)
        ghenv.Component.AddRuntimeMessage(w, msg)
    else:
        daylight_sig = "DAYLIGHT PREPROCESSING IN PROGRESS...\n"
        errors_dl = []
        
        # 优化点 2：使用 with open 并配合迭代器逐行读取，不把整个文件加载进内存
        with open(daylight_log_path, "r") as f:
            for line in f:
                line_lower = line.lower()
                if "error" in line_lower:
                    errors_dl.append(line)
                elif "successfully finished" in line_lower:
                    daylight_sig = "DAYLIGHT PREPROCESSING COMPLETED!\n"
                    break
        
        if errors_dl:
            daylight_sig = "DAYLIGHT PREPROCESSING CRASHED! CHECK BELOW FOR MESSAGES!\n"
            ghenv.Component.AddRuntimeMessage(err, daylight_sig)
            message_buffer.append(daylight_sig)
            message_buffer.extend(errors_dl)
        else:
            message_buffer.append(daylight_sig)

    message_buffer.append("---------------------------------------------\n")

    # --- 扫描 Thermal 日志 ---
    if not thermal_log_path:
        msg = "You don't have Thermal log file. \nPlease run Thermal Simulation or check VariantsName!\n"
        print(msg)
        message_buffer.append(msg)
        ghenv.Component.AddRuntimeMessage(w, msg)
    else:
        fatal_errors = 0
        errors_th = []
        
        with open(thermal_log_path, "r") as f:
            # 优化点 3：通过文件迭代器获取后续行，彻底废弃 dummy_log 字典
            iterator = iter(f)
            for line in iterator:
                if "Fatal Error at time" in line:
                    fatal_errors += 1
                    errors_th.append(line)
                    # 抓取报错后的连续4行
                    for _ in range(4):
                        try:
                            errors_th.append(next(iterator))
                        except StopIteration:
                            break
        
        if fatal_errors > 0:
            thermal_sig = "THERMAL SIMULATION CRASHED! CHECK BELOW FOR ERROR MESSAGES!\n"
            ghenv.Component.AddRuntimeMessage(err, thermal_sig)
            message_buffer.append(thermal_sig)
            message_buffer.extend(errors_th)
        else:
            msg = "THERMAL SIMULATION COMPLETED!\n"
            print(msg)
            message_buffer.append(msg)

# 执行逻辑
log_paths = find_log(ProjectFolder, variant_name)
scan_log_file(log_paths)

# 优化点 4：一次性更新组件的 Message，避免在循环中触发 UI 重绘
final_message = "".join(message_buffer)
ghenv.Component.Message = final_message
output = final_message