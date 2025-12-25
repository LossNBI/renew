# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.json', '.'),      # 루트에 config.json 포함
        ('data', 'data'),          # data 폴더와 그 내부 파일/폴더 전체 포함
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,  # 모든 바이너리 포함
    a.datas,     # 모든 데이터(위에서 설정한 datas) 포함
    [],
    name='LawViewer_Dist', # 실행 파일 이름을 원하는 대로 변경 가능
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,    # 용량을 줄이기 위해 UPX 압축 사용 (설치되어 있을 경우)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # GUI 프로그램이므로 콘솔 창이 뜨지 않게 설정
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'], # 아이콘 파일이 없다면 이 줄을 지우거나 이름을 맞추세요.
)