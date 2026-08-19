import asyncio
import edge_tts

async def main():
    voices = await edge_tts.list_voices()
    pt_voices = [v for v in voices if 'pt-BR' in v['Locale']]
    for v in pt_voices:
        print(f"{v['ShortName']} - {v['Gender']} - {v['FriendlyName']}")

asyncio.run(main())
