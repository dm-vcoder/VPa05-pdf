#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import pandas as pd
from pathlib import Path
import subprocess
import sys
from typing import List, Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors

class PDFGenerator:
    def __init__(self):
        self.data_dir = Path("data")
        self.templates_dir = Path("templates")
        self.output_dir = Path("output")
        
        # Создаем директории если их нет
        self.data_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        # Настройка стилей для ReportLab
        self.styles = getSampleStyleSheet()
        self.setup_fonts()
    
    def setup_fonts(self):
        """Настройка шрифтов для поддержки кириллицы"""
        try:
            # Пытаемся зарегистрировать системные шрифты
            import platform
            if platform.system() == "Windows":
                # Windows шрифты
                font_paths = [
                    "C:/Windows/Fonts/arial.ttf",
                    "C:/Windows/Fonts/calibri.ttf",
                    "C:/Windows/Fonts/tahoma.ttf"
                ]
            else:
                # macOS/Linux шрифты
                font_paths = [
                    "/System/Library/Fonts/Arial.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('CustomFont', font_path))
                        self.font_name = 'CustomFont'
                        return
                    except:
                        continue
            
            # Если не удалось загрузить кастомный шрифт, используем встроенный
            self.font_name = 'Helvetica'
        except:
            self.font_name = 'Helvetica'
    
    def get_available_files(self, directory: Path, extensions: List[str]) -> List[Path]:
        """Получить список файлов с указанными расширениями"""
        files = []
        for ext in extensions:
            files.extend(directory.glob(f"*.{ext}"))
        return sorted(files)
    
    def read_csv_file(self, file_path: Path) -> pd.DataFrame:
        """Читать CSV файл"""
        try:
            return pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            return pd.read_csv(file_path, encoding='cp1251')
    
    def read_json_file(self, file_path: Path) -> Dict[Any, Any]:
        """Читать JSON файл"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def read_html_template(self, file_path: Path) -> str:
        """Читать HTML шаблон"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def get_invoice_ids(self, data: Any) -> List[str]:
        """Получить список invoice_id из данных"""
        if isinstance(data, pd.DataFrame):
            if 'invoice_id' in data.columns:
                return data['invoice_id'].astype(str).tolist()
            elif 'id' in data.columns:
                return data['id'].astype(str).tolist()
        elif isinstance(data, dict):
            if 'invoices' in data:
                return [str(inv.get('id', inv.get('invoice_id', ''))) for inv in data['invoices']]
            elif isinstance(data, list):
                return [str(item.get('id', item.get('invoice_id', ''))) for item in data]
        return []
    
    def get_invoice_data(self, data: Any, invoice_id: str) -> Dict[str, Any]:
        """Получить данные конкретного инвойса"""
        if isinstance(data, pd.DataFrame):
            if 'invoice_id' in data.columns:
                row = data[data['invoice_id'].astype(str) == invoice_id]
            else:
                row = data[data['id'].astype(str) == invoice_id]
            
            if not row.empty:
                return row.iloc[0].to_dict()
        elif isinstance(data, dict):
            if 'invoices' in data:
                for inv in data['invoices']:
                    if str(inv.get('id', inv.get('invoice_id', ''))) == invoice_id:
                        return inv
        elif isinstance(data, list):
            for item in data:
                if str(item.get('id', item.get('invoice_id', ''))) == invoice_id:
                    return item
        
        return {}
    
    def generate_pdf(self, data: Dict[str, Any], output_path: Path) -> None:
        """Генерировать PDF из данных"""
        try:
            # Создаем PDF документ
            doc = SimpleDocTemplate(str(output_path), pagesize=A4, 
                                  rightMargin=20*mm, leftMargin=20*mm, 
                                  topMargin=20*mm, bottomMargin=20*mm)
            
            # Создаем стили
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=self.styles['Heading1'],
                fontName=self.font_name,
                fontSize=24,
                spaceAfter=30,
                alignment=1,  # Center
                textColor=colors.darkblue
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=self.styles['Heading2'],
                fontName=self.font_name,
                fontSize=16,
                spaceAfter=12,
                textColor=colors.darkblue
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=self.styles['Normal'],
                fontName=self.font_name,
                fontSize=12,
                spaceAfter=6
            )
            
            # Создаем содержимое PDF
            story = []
            
            # Заголовок
            story.append(Paragraph("СЧЕТ-ФАКТУРА", title_style))
            story.append(Paragraph(f"№ {data.get('invoice_id', 'N/A')}", normal_style))
            story.append(Spacer(1, 20))
            
            # Информация о клиенте и счете
            info_data = [
                ['Клиент:', data.get('customer_name', 'N/A')],
                ['Дата:', data.get('date', 'N/A')],
                ['Номер счета:', data.get('invoice_id', 'N/A')]
            ]
            
            info_table = Table(info_data, colWidths=[100, 200])
            info_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(info_table)
            story.append(Spacer(1, 20))
            
            # Сумма
            amount_style = ParagraphStyle(
                'AmountStyle',
                parent=self.styles['Heading2'],
                fontName=self.font_name,
                fontSize=20,
                alignment=1,  # Center
                textColor=colors.darkred,
                spaceAfter=20
            )
            story.append(Paragraph(f"Сумма: {data.get('amount', 'N/A')} ₽", amount_style))
            
            # Описание
            story.append(Paragraph("Описание услуг:", heading_style))
            story.append(Paragraph(data.get('description', 'N/A'), normal_style))
            story.append(Spacer(1, 30))
            
            # Подпись
            story.append(Paragraph("Спасибо за ваш заказ!", normal_style))
            story.append(Paragraph(f"Дата создания: {data.get('date', 'N/A')}", normal_style))
            
            # Строим PDF
            doc.build(story)
            print(f"✅ PDF успешно создан: {output_path}")
            
        except Exception as e:
            print(f"❌ Ошибка при создании PDF: {e}")
            raise
    
    def open_pdf(self, pdf_path: Path) -> None:
        """Открыть PDF в системной программе"""
        try:
            if sys.platform == "win32":
                os.startfile(str(pdf_path))
            elif sys.platform == "darwin":  # macOS
                subprocess.run(["open", str(pdf_path)])
            else:  # Linux
                subprocess.run(["xdg-open", str(pdf_path)])
            print(f"📄 PDF открыт в системной программе")
        except Exception as e:
            print(f"⚠️ Не удалось открыть PDF автоматически: {e}")
    
    def show_menu(self, title: str, items: List[str]) -> int:
        """Показать пронумерованное меню и получить выбор пользователя"""
        print(f"\n{'='*50}")
        print(f" {title}")
        print(f"{'='*50}")
        
        for i, item in enumerate(items, 1):
            print(f"{i:2d}. {item}")
        
        while True:
            try:
                choice = int(input(f"\nВыберите вариант (1-{len(items)}): "))
                if 1 <= choice <= len(items):
                    return choice - 1
                else:
                    print(f"❌ Введите число от 1 до {len(items)}")
            except ValueError:
                print("❌ Введите корректное число")
    
    def run(self):
        """Основной цикл программы"""
        print("🚀 PDF Generator - Генератор PDF документов")
        print("=" * 50)
        
        # Получаем доступные файлы данных
        data_files = self.get_available_files(self.data_dir, ['csv', 'json'])
        if not data_files:
            print("❌ В директории /data не найдено CSV или JSON файлов")
            return
        
        # Получаем доступные HTML шаблоны
        template_files = self.get_available_files(self.templates_dir, ['html', 'htm'])
        if not template_files:
            print("❌ В директории /templates не найдено HTML файлов")
            return
        
        # Показываем доступные файлы данных
        data_file_names = [f.name for f in data_files]
        data_choice = self.show_menu("Доступные файлы данных", data_file_names)
        selected_data_file = data_files[data_choice]
        
        # Показываем доступные шаблоны
        template_file_names = [f.name for f in template_files]
        template_choice = self.show_menu("Доступные HTML шаблоны", template_file_names)
        selected_template_file = template_files[template_choice]
        
        print(f"\n📁 Выбран файл данных: {selected_data_file.name}")
        print(f"📄 Выбран шаблон: {selected_template_file.name}")
        
        # Загружаем данные
        print("\n📖 Загружаем данные...")
        if selected_data_file.suffix.lower() == '.csv':
            data = self.read_csv_file(selected_data_file)
        else:
            data = self.read_json_file(selected_data_file)
        
        # Получаем список invoice_id
        invoice_ids = self.get_invoice_ids(data)
        if not invoice_ids:
            print("❌ В файле данных не найдено invoice_id")
            return
        
        # Показываем доступные инвойсы
        invoice_choice = self.show_menu("Доступные инвойсы", invoice_ids)
        selected_invoice_id = invoice_ids[invoice_choice]
        
        print(f"\n📋 Выбран инвойс: {selected_invoice_id}")
        
        # Получаем данные инвойса
        invoice_data = self.get_invoice_data(data, selected_invoice_id)
        if not invoice_data:
            print("❌ Данные для выбранного инвойса не найдены")
            return
        
        # Создаем имя файла PDF
        pdf_filename = f"invoice_{selected_invoice_id}.pdf"
        pdf_path = self.output_dir / pdf_filename
        
        # Генерируем PDF
        print("📄 Создаем PDF...")
        self.generate_pdf(invoice_data, pdf_path)
        
        # Открываем PDF
        print("🚀 Открываем PDF...")
        self.open_pdf(pdf_path)
        
        print(f"\n✅ Готово! PDF сохранен: {pdf_path}")

def main():
    """Точка входа в программу"""
    try:
        generator = PDFGenerator()
        generator.run()
    except KeyboardInterrupt:
        print("\n\n👋 Программа прервана пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
