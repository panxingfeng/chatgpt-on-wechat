基于chatgpt-on-wechat的插件开发

包括：图像识别、网页搜索、论文搜索

使用本地ollama模型，可以使用qwen2作为模型的选择

图像识别使用的模型是：MiniCPM-Llama3-V-2_5 19G版本

支持图像识别需要修改的代码处，channel文件夹下的wechat下的wechat_channel.py文件

修改的代码是：


{

@itchat.msg_register([TEXT, VOICE, PICTURE, NOTE, ATTACHMENT, SHARING])


def handler_single_msg(msg):

    try:
    
        cmsg = WechatMessage(msg, False)
        
        if cmsg.ctype == ContextType.IMAGE:
        
            file_dir = ''  # 设置图片临时保存路径
            
            if not os.path.exists(file_dir):
            
                os.makedirs(file_dir)


            file_path = os.path.join(file_dir, cmsg.msg_id + ".jpg")
            
            msg.download(file_path)  # 下载图片到指定路径
            
            logger.info(f"[WX] Image saved to {file_path}")
            

            # 更新内容为文件路径，传递给处理函数
            
            cmsg.content = file_path
            
            WechatChannel().handle_single(cmsg)
            
        else:

            WechatChannel().handle_single(cmsg)
            
    except NotImplementedError as e:
    
        logger.debug("[WX] single message {} skipped: {}".format(msg["MsgId"], e))
        
        return None
        
}
