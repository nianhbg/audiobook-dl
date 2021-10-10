from ..utils.source import Source
from PIL import Image
import io


class ScribdSource(Source):
    match = [
        r"https?://(www)?.scribd.com/listen/\d+",
        r"https?://(www)?.scribd.com/audiobook/\d+/"
    ]
    require_cookies = True

    def get_title(self):
        if self.meta['title'][-5:] == ", The":
            split = self.meta['title'].split(', ')
            if len(split) == 2:
                return f"{split[1]} {split[0]}"
        return self.meta['title']

    def get_cover(self):
        # Downloading image from scribd
        raw_cover = self.get(self.meta["cover_url"])
        # Removing padding on the top and bottom
        im = Image.open(io.BytesIO(raw_cover))
        width, height = im.size
        cropped = im.crop((0, (height-width)/2, width, width+(height-width)/2))
        cover = io.BytesIO()
        cropped.save(cover, format="jpeg")
        return cover.getvalue()

    def get_metadata(self):
        metadata = {}
        if len(self.meta["authors"]):
            metadata["author"] = "; ".join(self.meta["authors"])
        if len(self.meta["series"]):
            metadata["series"] = self.meta["series"][0]
        return metadata

    def get_files(self):
        files = []
        for part, i in enumerate(self.media["playlist"]):
            chapter = i["chapter_number"]
            chapter_str = "0"*(3-len(str(part)))+str(part)
            files.append({
                "url": i["url"],
                "title": f"Chapter {chapter}",
                "part": chapter_str,
                "ext": "mp3"
            })
        return files

    def before(self, *args):
        if self.match_num == 1:
            book_id = self.url.split("/")[4]
            self.url = f"https://www.scribd.com/listen/{book_id}"
        user_id = self.find_in_page(
                self.url,
                r'(?<=(account_id":"scribd-))\d+')
        book_id = self.find_in_page(
                self.url,
                r'(?<=(external_id":"))\d+')
        headers = {
            'Session-Key': self.find_in_page(
                self.url,
                '(?<=(session_key":"))[^"]+')
        }
        misc = self.get_json(
            f"https://api.findawayworld.com/v4/accounts/scribd-{user_id}/audiobooks/{book_id}",
            headers=headers,
        )
        self.meta = misc['audiobook']
        self.media = self.post_json(
            f"https://api.findawayworld.com/v4/audiobooks/{book_id}/playlists",
            headers=headers,
            json={
                "license_id": misc['licenses'][0]['id']
            }
        )
        self.misc = misc