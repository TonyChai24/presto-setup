#!/usr/bin/env python2
# coding=utf-8
import os, sys

##  print sys.path[0],'------' ###获取当前文件的所在的绝对路径
pwd = sys.path[0]  # 当前路径
#print sys.argv[1]
if len(sys.argv)<2:
    print '请传入安装路径 格式:./setup.py 安装路径'
    exit(0)
setup_path = sys.argv[1]
# --去掉结尾的/
if setup_path[-1] == '/':
    setup_path = setup_path[:-1]
# setup_path='/opt/presto-server-0.147'     #待安装到的目录

# ----------------------配置验证------------------------------------
# coordinator　协调者
coordinator = '''
coordinator=true
node-scheduler.include-coordinator=false
discovery-server.enabled=true
'''
# worker　工作者
worker = '''
coordinator=false
'''

# local　　协调and工作者(local 和小集群才使用)
local = '''
coordinator=true
node-scheduler.include-coordinator=true
discovery-server.enabled=true
'''

node={}
jvm_config=''
log_properties=''
try:
    import conf
    coordinator = coordinator.strip()+'\n'+conf.allconf.strip()
    worker = worker.strip()+'\n'+conf.allconf.strip()
    local = local.strip() +'\n'+ conf.allconf.strip()
    #print coordinator,'\n'
    #print worker,'\n'
    #print local,'\n'

    jvm_config = conf.jvm_config.strip()
    log_properties = conf.log_properties.strip()

except Exception as e:
    print 'conf.py配置有错误', e
    exit(0)

# ----------------------------------验证结束-------------------------------------

##################用于找出 所有的master和slave名称
def listwork(path):
    rd = open(path, 'r+')
    line = rd.readline().strip()  # 读取一行
    tmp = []
    while line:
        if not ('#' in line or line == '\n'):
            tmp.append(line)
        line = rd.readline().strip()  # 读取一行
    rd.close()
    # print tmp
    return tmp
#######################################
# 把字典转换成文本
def getNodeconf(host):
    node = conf.node
    #print node
    outtmp = ''
    for line in node.split('\n'):
        if 'node.id' in line:  ##node 中有node.id字段需要替换
            outtmp += line.replace('*','')+host+'\n'
        elif 'node.data-dir' in line:
            outtmp += 'node.data-dir=' + setup_path + '/data' + '\n'
        else:
            outtmp += line + '\n'
    return outtmp

###############
'''
注意！
本程序从msater 节点开始会分发程序，进行配置 并完成安装
'''
if __name__ == '__main__':
    print '''
*************************************************************
因产线环境多为jdk1.7 友情建议 可以内置一个jre:
    '''
    print '****************************************************************************'
    JAVA_HOME=__import__('conf').JAVA_HOME
    print '您配置的java8　路径为:',JAVA_HOME
    if os.path.exists(pwd+'/catalog/hive.properties'):
        print '发现catalog/hive.properties连接器　您的配置如下:\n'
        os.system('cat '+pwd+'/catalog/hive.properties')
    print '*****************************************************************************'
    ok = raw_input('\n即将安装presto到:' + setup_path + '目录下\n 您确认以上配置后是否继续安装(y or n)? ')
    if ok not in ['y', 'Y']:
        print '未输入y 取消安装'
        exit(0)

    ##清理可能存在的垃圾
    os.system('rm -rf ' + pwd + '/../data')  ## rm data
    os.system('rm -rf ' + pwd + '/../etc')
    os.system('mkdir -p '+pwd + '/../etc')
    os.system('echo \''+jvm_config+'\' > '+pwd+'/../etc/jvm.config')
    os.system('echo \''+log_properties+'\' > '+pwd+'/../etc/log.properties')
    os.system('cp -rf ' + pwd + '/catalog ' + pwd + '/../etc')

    ## 获取节点列表
    master = listwork(pwd + '/master')
    slaves = listwork(pwd + '/slaves')
    print 'master=', master
    print 'slaves=', slaves
    #### 下面开始 合并 分发文件
    nameall = reduce(lambda x, y: x if y in x else x + [y], [[], ] + master + slaves)  ##去重复 合并
    print nameall
    scpok = 1  ##0 是完成
    for i in nameall:
        print 'next setup ' + i + '-----------------------------'
        cmd = 'scp -r ' + pwd + '/../* ' + i + ':' + setup_path + '/'
        print cmd
        os.system('ssh ' + i + '  mkdir -p ' + setup_path)  ##创建目录
        scpok = os.system(cmd)  ##发送
        if scpok == 0:
            print i, 'scp 发送完成'
        else:
            print i, 'scp 发送失败!'
    ### 下面开始 config 配置文件安装

    for i in nameall:
        if i in slaves:
            if i in master:  ## in master and slaves
                print i, ' 是local模式节点 next setup local!'
                os.system('ssh ' + i + '  \'echo \"' + local + '\" > ' + setup_path + '/etc/config.properties\'')
            else:  ## in slaves
                print i, 'setup slave节点'
                os.system('ssh ' + i + '  \'echo \"' + worker + '\" > ' + setup_path + '/etc/config.properties\'')
        else:  ## in master
            print i, 'setup master节点'
            os.system('ssh ' + i + '  \'echo \"' + coordinator + '\" > ' + setup_path + '/etc/config.properties\'')

        ### 下面进行node 设置
        os.system('ssh ' + i + '  \'echo \"' + getNodeconf(i) + '\" > ' + setup_path + '/etc/node.properties\'')


