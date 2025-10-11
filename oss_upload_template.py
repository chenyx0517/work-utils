#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSS上传接口模板
替换font_splitter.py中的mock_upload_to_cdn函数
"""

import os
import hashlib
from typing import Optional

# 根据你使用的OSS服务商选择对应的SDK
# 示例1: 阿里云OSS
try:
    import oss2
    OSS_TYPE = 'aliyun'
except ImportError:
    OSS_TYPE = None

# 示例2: 腾讯云COS
try:
    from qcloud_cos import CosConfig, CosS3Client
    OSS_TYPE = 'tencent'
except ImportError:
    pass

# 示例3: AWS S3
try:
    import boto3
    OSS_TYPE = 'aws'
except ImportError:
    pass

class OSSUploader:
    """OSS上传器基类"""
    
    def __init__(self, config: dict):
        self.config = config
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化OSS客户端"""
        raise NotImplementedError
    
    def upload_file(self, local_file_path: str, remote_file_path: str) -> Optional[str]:
        """上传文件到OSS"""
        raise NotImplementedError

class AliyunOSSUploader(OSSUploader):
    """阿里云OSS上传器"""
    
    def _init_client(self):
        auth = oss2.Auth(
            self.config['access_key_id'],
            self.config['access_key_secret']
        )
        self.client = oss2.Bucket(
            auth,
            self.config['endpoint'],
            self.config['bucket_name']
        )
    
    def upload_file(self, local_file_path: str, remote_file_path: str) -> Optional[str]:
        try:
            result = self.client.put_object_from_file(remote_file_path, local_file_path)
            if result.status == 200:
                return f"https://{self.config['bucket_name']}.{self.config['endpoint']}/{remote_file_path}"
            return None
        except Exception as e:
            print(f"阿里云OSS上传失败: {e}")
            return None

class TencentCOSUploader(OSSUploader):
    """腾讯云COS上传器"""
    
    def _init_client(self):
        config = CosConfig(
            Region=self.config['region'],
            SecretId=self.config['secret_id'],
            SecretKey=self.config['secret_key']
        )
        self.client = CosS3Client(config)
    
    def upload_file(self, local_file_path: str, remote_file_path: str) -> Optional[str]:
        try:
            response = self.client.upload_file(
                Bucket=self.config['bucket_name'],
                LocalFilePath=local_file_path,
                Key=remote_file_path
            )
            if response.get('ETag'):
                return f"https://{self.config['bucket_name']}.cos.{self.config['region']}.myqcloud.com/{remote_file_path}"
            return None
        except Exception as e:
            print(f"腾讯云COS上传失败: {e}")
            return None

class AWSS3Uploader(OSSUploader):
    """AWS S3上传器"""
    
    def _init_client(self):
        self.client = boto3.client(
            's3',
            aws_access_key_id=self.config['access_key_id'],
            aws_secret_access_key=self.config['access_key_secret'],
            region_name=self.config['region']
        )
    
    def upload_file(self, local_file_path: str, remote_file_path: str) -> Optional[str]:
        try:
            self.client.upload_file(
                local_file_path,
                self.config['bucket_name'],
                remote_file_path
            )
            return f"https://{self.config['bucket_name']}.s3.{self.config['region']}.amazonaws.com/{remote_file_path}"
        except Exception as e:
            print(f"AWS S3上传失败: {e}")
            return None

def create_oss_uploader(oss_type: str, config: dict) -> OSSUploader:
    """创建OSS上传器"""
    if oss_type == 'aliyun':
        return AliyunOSSUploader(config)
    elif oss_type == 'tencent':
        return TencentCOSUploader(config)
    elif oss_type == 'aws':
        return AWSS3Uploader(config)
    else:
        raise ValueError(f"不支持的OSS类型: {oss_type}")

def upload_to_oss(font_file_path: str, cdn_base_url: str, language: str, oss_config: dict) -> str:
    """
    上传字体文件到OSS
    
    参数:
    - font_file_path: 本地字体文件路径
    - cdn_base_url: CDN基础URL
    - language: 语言标识
    - oss_config: OSS配置
    
    返回:
    - CDN URL
    """
    # 生成文件名hash，避免重名
    with open(font_file_path, 'rb') as f:
        file_hash = hashlib.md5(f.read()).hexdigest()[:8]
    
    filename = os.path.basename(font_file_path)
    name, ext = os.path.splitext(filename)
    cdn_filename = f"{name}_{file_hash}{ext}"
    
    # 构建远程文件路径
    remote_file_path = f"{language}/{cdn_filename}"
    
    # 创建OSS上传器
    oss_type = oss_config.get('type', 'aliyun')
    uploader = create_oss_uploader(oss_type, oss_config)
    
    # 上传文件
    cdn_url = uploader.upload_file(font_file_path, remote_file_path)
    
    if cdn_url:
        print(f"  ✅ OSS上传成功: {font_file_path} -> {cdn_url}")
        return cdn_url
    else:
        print(f"  ❌ OSS上传失败: {font_file_path}")
        # 返回Mock URL作为备用
        return f"{cdn_base_url}/{language}/{cdn_filename}"

# 配置示例
OSS_CONFIG_EXAMPLES = {
    'aliyun': {
        'type': 'aliyun',
        'access_key_id': 'your-access-key-id',
        'access_key_secret': 'your-access-key-secret',
        'endpoint': 'oss-cn-hangzhou.aliyuncs.com',
        'bucket_name': 'your-bucket-name'
    },
    'tencent': {
        'type': 'tencent',
        'secret_id': 'your-secret-id',
        'secret_key': 'your-secret-key',
        'region': 'ap-beijing',
        'bucket_name': 'your-bucket-name'
    },
    'aws': {
        'type': 'aws',
        'access_key_id': 'your-access-key-id',
        'access_key_secret': 'your-access-key-secret',
        'region': 'us-east-1',
        'bucket_name': 'your-bucket-name'
    }
}

if __name__ == "__main__":
    print("OSS上传接口模板")
    print("=" * 50)
    print("使用方法:")
    print("1. 根据你的OSS服务商选择对应的配置")
    print("2. 安装相应的SDK:")
    print("   - 阿里云OSS: pip install oss2")
    print("   - 腾讯云COS: pip install cos-python-sdk-v5")
    print("   - AWS S3: pip install boto3")
    print("3. 在font_splitter.py中替换mock_upload_to_cdn函数")
    print("4. 配置OSS参数")
    
    print("\n配置示例:")
    for provider, config in OSS_CONFIG_EXAMPLES.items():
        print(f"\n{provider.upper()}:")
        for key, value in config.items():
            print(f"  {key}: {value}")
