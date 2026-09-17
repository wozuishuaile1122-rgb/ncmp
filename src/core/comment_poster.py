import json
import random
import time
from typing import Optional

import requests

from ..utils.comments import CommentGenerator
from ..utils.config import Config
from ..utils.logger import Logger


class CommentPoster:
    """评分后为歌曲发布留言，获取留言积分（+1分/首，每日上限20分）"""

    COMMENT_URL = "https://music.163.com/weapi/v1/resource/comments/R_SO_4_{song_id}"

    def __init__(self, session: requests.Session, logger: Logger, config: Config):
        self.session = session
        self.logger = logger
        self.config = config

        # 加密相关常量（与 Signer 相同）
        from ..core.signer import Signer
        self._signer = Signer(session, "", logger, config)

    def post_comment(self, work: dict, score: str) -> bool:
        """为歌曲发布评论/留言
        
        Args:
            work: 歌曲信息字典，需包含 resourceId 和 name
            score: 评分字符串，用于生成对应风格的评论
            
        Returns:
            是否发布成功
        """
        try:
            song_id = work.get("resourceId", "")
            if not song_id:
                self.logger.warning(f"歌曲「{work.get('name', '未知')}」缺少 resourceId，跳过留言")
                return False

            csrf = str(self.session.cookies["__csrf"])
            comment_text = CommentGenerator.generate(score)

            # 构造评论请求数据
            data = {
                "threadId": f"R_SO_4_{song_id}",
                "content": comment_text,
                "csrf_token": csrf
            }

            params = {
                "params": self._signer._get_params(data),
                "encSecKey": self._signer._get_enc_sec_key()
            }

            url = self.COMMENT_URL.format(song_id=song_id)
            response = self.session.post(
                url=f"{url}?csrf_token={csrf}",
                data=params,
                headers={"Referer": "https://music.163.com/"}
            ).json()

            if response.get("code") == 200:
                self.logger.info(f"歌曲「{work['name']}」留言成功：{comment_text}")
                return True
            else:
                error_msg = response.get("message") or response.get("msg", "未知错误")
                self.logger.warning(f"歌曲「{work['name']}」留言失败：{error_msg}")
                return False

        except Exception as e:
            self.logger.warning(f"歌曲「{work.get('name', '未知')}」留言异常：{str(e)}")
            return False
