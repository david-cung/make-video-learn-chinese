import copy,json,unittest,urllib.request,urllib.error,pathlib
from lesson_planner import plan_topic,validate,LESSONS

class Lessons(unittest.TestCase):
    def test_all_built_in_lessons(self):
        for item in LESSONS:
            p=plan_topic(item['keys'][0])
            self.assertEqual(len(p['scenes']),5)
            self.assertTrue(any(s['lang']=='zh' for s in p['scenes']))
    def test_dictionary_lookup(self):
        self.assertEqual(plan_topic('uống nước')['source'],'Từ vựng HSK có sẵn')
    def test_rejects_vietnamese_transliteration_and_pinyin(self):
        for text in ['Nỉ hảo nhé','nǐ hǎo','你好']:
            p=plan_topic('cà phê');p['scenes'][0]['text']=text
            with self.assertRaises(ValueError): validate(p)
    def test_chinese_speech_must_use_hanzi(self):
        p=plan_topic('cà phê');p['scenes'][1]['text']='ka fei'
        with self.assertRaises(ValueError):validate(p)
    def test_long_script_rejected(self):
        p=plan_topic('cà phê')
        for s in p['scenes']:
            if s['lang']=='vi':s['text']='xin chào '*25
        with self.assertRaises(ValueError):validate(p)
    def test_no_unrelated_fallback(self):
        with self.assertRaises(ValueError):plan_topic('chủ đề hoàn toàn chưa được định nghĩa xyz')

if __name__=='__main__':unittest.main()
