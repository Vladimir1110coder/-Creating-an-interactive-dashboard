import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

df_raw = None 
df_work = None 
df_filtered = None 
VARIANT_NUMBER = 10
fig = plt.Figure(figsize=(9, 5.5), dpi=100)
canvas = None
current_chart = "line"

plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans']
plt.rcParams['axes.unicode_minus'] = False

df_raw = pd.read_csv(r'C:\Users\User\Desktop\Л7\data.csv')


def preprocess_data():

    df_work = df_raw.copy()

    #Фильтрация

    mask = (df_work['dist'] < 0) | (df_work['pace'] < 0)

    df_work = df_work[~mask]

    df_work['cal'] = np.where(df_work['cal'] < 0, 0, df_work['cal'])

    q10, q90 = np.nanpercentile(df_work['pace'], [10, 90])

    df_work['pace'] = np.clip(df_work['pace'], q10, q90)

    #Создание новых признаков

    df_work["distance_group"] = np.where(df_work["dist"] < 5, "short", np.where(df_work["dist"] <= 10, "medium", "long"))

    df_work['calorie_burn_group'] = np.where(
    df_work['cal'] < 300, 'low',
    np.where(
        df_work['cal'] < 600, 'medium',
        np.where(
            df_work['cal'] < 900, 'high',
            'very_high'
        )
      )
    )

    df_work["speed_km"] = np.where(df_work["pace"] > 0, 60 / df_work["pace"], np.nan)


    athlete_median_speed = df_work.groupby('ts')['speed_km'].transform('median')

    speed_ratio = df_work['speed_km'] / athlete_median_speed


    df_work['relative_speed_cat'] = 'base'
    df_work.loc[speed_ratio < 0.85, 'relative_speed_cat'] = 'low'
    df_work.loc[(speed_ratio >= 0.85) & (speed_ratio < 1.0), 'relative_speed_cat'] = 'sub_avg'
    df_work.loc[(speed_ratio >= 1.0) & (speed_ratio < 1.15), 'relative_speed_cat'] = 'above_avg'
    df_work.loc[speed_ratio >= 1.15, 'relative_speed_cat'] = 'peak'
    df_work.loc[df_work['speed_km'].isna(), 'relative_speed_cat'] = np.nan

    #3. Обрезка выбросов

    columns = ["dist", "pace", "cal", "zone", "speed_km"]
   

    for col in columns:
        col_data = df_work[col]
        col_sort = col_data.sort_values()
        median_col = col_sort.median()
        Q1 = np.nanpercentile(col_sort, 25)
        Q3 = np.nanpercentile(col_sort, 75)
        IQR = Q3 - Q1
        lower_limit = Q1 - 1.5 * IQR
        upper_limit = Q3 + 1.5 * IQR
        
        is_outlier = (col_data < lower_limit) | (col_data > upper_limit)
        

        df_work[col] = np.where(is_outlier, median_col, col_data)

    return df_work    


root = tk.Tk()
root.title(f"Дашборд: Вариант {VARIANT_NUMBER}")
root.geometry("1200x800")
root.configure(bg="#f0f2f5")

# Создаем панель фильтров
# Создаем панель фильтров
# === ПАНЕЛЬ ФИЛЬТРОВ (исправленная сетка) ===
filter_frame = tk.Frame(root, bg="#e1e5eb")
filter_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

# Ряд 0: Динамические фильтры
tk.Label(filter_frame, text="Группа дистанции:", bg="#e1e5eb").grid(row=0, column=0, padx=5, pady=4, sticky='w')
distance_filter = ttk.Combobox(filter_frame, values=["Все", "short", "medium", "long"], state="readonly", width=12)
distance_filter.set("Все")
distance_filter.grid(row=0, column=1, padx=5, pady=4, sticky='w')

tk.Label(filter_frame, text="Группа калорий:", bg="#e1e5eb").grid(row=0, column=2, padx=15, pady=4, sticky='w')
calorie_filter = ttk.Combobox(filter_frame, values=["Все", "low", "medium", "high", "very_high"], state="readonly", width=12)
calorie_filter.set("Все")
calorie_filter.grid(row=0, column=3, padx=5, pady=4, sticky='w')

# Ряд 1: Агрегация и Сглаживание
tk.Label(filter_frame, text="Агрегация:", bg="#e1e5eb").grid(row=1, column=0, padx=5, pady=4, sticky='w')
agg_var = tk.StringVar(value="mean")
agg_frame = tk.Frame(filter_frame, bg="#e1e5eb")
agg_frame.grid(row=1, column=1, padx=5, pady=4, sticky='w')
tk.Radiobutton(agg_frame, text="Среднее", variable=agg_var, value="mean", bg="#e1e5eb").pack(side=tk.LEFT, padx=2)
tk.Radiobutton(agg_frame, text="Сумма", variable=agg_var, value="sum", bg="#e1e5eb").pack(side=tk.LEFT, padx=2)
tk.Radiobutton(agg_frame, text="Медиана", variable=agg_var, value="median", bg="#e1e5eb").pack(side=tk.LEFT, padx=2)

tk.Label(filter_frame, text="Сглаживание:", bg="#e1e5eb").grid(row=1, column=2, padx=15, pady=4, sticky='w')
smooth_var = tk.BooleanVar(value=False)
smooth_frame = tk.Frame(filter_frame, bg="#e1e5eb")
smooth_frame.grid(row=1, column=3, padx=5, pady=4, sticky='w')
tk.Checkbutton(smooth_frame, text="Вкл", variable=smooth_var, bg="#e1e5eb").pack(side=tk.LEFT)

# Ряд 2: Период и Биннинг
tk.Label(filter_frame, text="Период:", bg="#e1e5eb").grid(row=2, column=0, padx=5, pady=4, sticky='w')
period_var = tk.StringVar(value="D")
period_frame = tk.Frame(filter_frame, bg="#e1e5eb")
period_frame.grid(row=2, column=1, padx=5, pady=4, sticky='w')
tk.Radiobutton(period_frame, text="День", variable=period_var, value="D", bg="#e1e5eb").pack(side=tk.LEFT, padx=2)
tk.Radiobutton(period_frame, text="Неделя", variable=period_var, value="W", bg="#e1e5eb").pack(side=tk.LEFT, padx=2)
tk.Radiobutton(period_frame, text="Месяц", variable=period_var, value="M", bg="#e1e5eb").pack(side=tk.LEFT, padx=2)

tk.Label(filter_frame, text="Биннинг:", bg="#e1e5eb").grid(row=2, column=2, padx=15, pady=4, sticky='w')
bin_var = tk.StringVar(value="distance_group")
bin_combo = ttk.Combobox(filter_frame, textvariable=bin_var, 
                         values=["distance_group", "calorie_burn_group", "relative_speed_cat"], 
                         state="readonly", width=18)
bin_combo.grid(row=2, column=3, padx=5, pady=4, sticky='w')

# === Инициализация переменных для осей и Heatmap ===
x_axis_var = tk.StringVar(value="ts")
y_axis_var = tk.StringVar(value="dist")
hm_index_var = tk.StringVar(value="zone")
hm_col_var = tk.StringVar(value="cal")

# Ряд 3: Выбор осей для графиков (ОТДЕЛЬНАЯ СТРОКА!)
tk.Label(filter_frame, text="Ось X:", bg="#e1e5eb").grid(row=3, column=0, padx=5, pady=4, sticky='w')
x_axis_combo = ttk.Combobox(filter_frame, textvariable=x_axis_var, 
                            values=["ts", "dist", "pace", "cal", "zone"], 
                            state="readonly", width=12)
x_axis_combo.grid(row=3, column=1, padx=5, pady=4, sticky='w')

tk.Label(filter_frame, text="Ось Y:", bg="#e1e5eb").grid(row=3, column=2, padx=15, pady=4, sticky='w')
y_axis_combo = ttk.Combobox(filter_frame, textvariable=y_axis_var, 
                            values=["dist", "pace", "cal", "zone"], 
                            state="readonly", width=12)
y_axis_combo.grid(row=3, column=3, padx=5, pady=4, sticky='w')

# Ряд 4: Настройки тепловой карты (ОТДЕЛЬНАЯ СТРОКА!)
tk.Label(filter_frame, text="HM строки", bg="#e1e5eb").grid(row=4, column=0, padx=5, pady=4, sticky='w')
hm_index_combo = ttk.Combobox(filter_frame, textvariable=hm_index_var, 
                              values=["zone", "distance_group", "calorie_burn_group"], 
                              state="readonly", width=18)
hm_index_combo.grid(row=4, column=1, columnspan=2, padx=5, pady=4, sticky='w')

tk.Label(filter_frame, text="HM столбцы", bg="#e1e5eb").grid(row=4, column=3, padx=5, pady=4, sticky='w')
hm_col_combo = ttk.Combobox(filter_frame, textvariable=hm_col_var, 
                            values=["cal", "dist", "pace", "zone"], 
                            state="readonly", width=12)
hm_col_combo.grid(row=4, column=4, padx=5, pady=4, sticky='w')

# Ряд 5: Кнопка применения
apply_btn = tk.Button(filter_frame, text="Применить фильтры", command=lambda: apply_filters(), 
                     bg="#4CAF50", fg="white", width=20, height=2)
apply_btn.grid(row=5, column=0, columnspan=5, pady=10)

# Настройка весов колонок (теперь 5 колонок: 0,1,2,3,4)
for i in range(5):
    filter_frame.grid_columnconfigure(i, weight=1)

# Настройка весов колонок для равномерного распределения
filter_frame.grid_columnconfigure(0, weight=1)
filter_frame.grid_columnconfigure(1, weight=2)
filter_frame.grid_columnconfigure(2, weight=1)
filter_frame.grid_columnconfigure(3, weight=2)

ctrl_frame = tk.Frame(root, bg="#f0f2f5", height=45)
ctrl_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

plot_frame = tk.Frame(root, bg="white", relief=tk.SUNKEN, bd=1)
plot_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

canvas = FigureCanvasTkAgg(fig, master=plot_frame)
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

toolbar = NavigationToolbar2Tk(canvas, plot_frame)
toolbar.update()
toolbar.pack(side=tk.TOP, fill=tk.X)   

#Графики

def clear_figure():
    fig.clear() 

def sample_data(df, max_points=5000):
    """Уменьшает количество точек для отрисовки"""
    if len(df) > max_points:
        return df.iloc[::len(df)//max_points]
    return df

def apply_filters():
    
    global df_filtered
    
    
    df_filtered = df_work.copy()
    
   
    if distance_filter.get() != "Все":
        df_filtered = df_filtered[df_filtered["distance_group"] == distance_filter.get()]
    
    
    if calorie_filter.get() != "Все":
        df_filtered = df_filtered[df_filtered["calorie_burn_group"] == calorie_filter.get()]
    
   
    if smooth_var.get():
        df_filtered['dist_smooth'] = df_filtered['dist'].rolling(window=3, center=True).mean()
    
    
    if current_chart == "line": plot_line()
    elif current_chart == "bar": plot_bar()
    elif current_chart == "scatter": plot_scatter()
    else: plot_heat_map()

def get_plot_data():
    
    if df_filtered is not None and len(df_filtered) > 0:
        return df_filtered.copy()
    else:
        return df_work.copy()

def plot_line():
    global current_chart
    current_chart = "line"
    clear_figure()
    ax = fig.add_subplot(111)
    
    df_plot = get_plot_data()
    
    x_col = x_axis_var.get()
    y_col = y_axis_var.get()
    
    if x_col not in df_plot.columns or y_col not in df_plot.columns:
        ax.set_title("❌ Выбранная колонка не найдена")
        fig.tight_layout()
        canvas.draw_idle()
        return
    
    df_plot = df_plot.dropna(subset=[x_col, y_col]).sort_values(x_col)
    
    if smooth_var.get() and y_col == 'dist' and 'dist_smooth' in df_plot.columns:
        y_data = df_plot['dist_smooth']
        label = f'{y_col} (сглаж.)'
    else:
        y_data = df_plot[y_col]
        label = y_col
    
    df_plot = sample_data(df_plot)
    
    sns.lineplot(data=df_plot, x=x_col, y=y_data, ax=ax, label=label)

    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(f"{y_col} от {x_col} (записей: {len(df_plot)})")
    ax.legend()
    ax.tick_params(axis='x', rotation=45)

    fig.tight_layout()
    canvas.draw_idle()


def plot_bar():
    global current_chart
    current_chart = "bar"
    clear_figure()
    ax = fig.add_subplot(111)

    df_plot = get_plot_data()
    
    agg_func = agg_var.get()
    value_col = y_axis_var.get()   # dist/pace/cal/zone
    group_col = bin_var.get()      # группировка
    
    if value_col not in df_plot.columns or group_col not in df_plot.columns:
        ax.set_title("❌ Колонка не найдена")
        fig.tight_layout()
        canvas.draw_idle()
        return
    
    aggregated_data = df_plot.groupby(group_col)[value_col].agg(agg_func).reset_index()

    sns.barplot(data=aggregated_data, x=group_col, y=value_col, ax=ax)

    ax.set_xlabel("Группа")
    ax.set_ylabel(f"{agg_func.capitalize()} {value_col}")
    ax.set_title(f"{value_col} по {group_col}")
    ax.tick_params(axis='x', rotation=45)

    fig.tight_layout()
    canvas.draw_idle()


def plot_scatter():
    global current_chart
    current_chart = "scatter"
    clear_figure()
    ax = fig.add_subplot(111)

    df_plot = get_plot_data()
    
    x_col = x_axis_var.get()
    y_col = y_axis_var.get()
    
    if x_col not in df_plot.columns or y_col not in df_plot.columns:
        ax.set_title("❌ Колонка не найдена")
        fig.tight_layout()
        canvas.draw_idle()
        return
    
    df_plot = df_plot.dropna(subset=[x_col, y_col])
    
    if len(df_plot) == 0:
        ax.set_title("Нет данных после фильтрации")
        fig.tight_layout()
        canvas.draw_idle()
        return
    
    df_plot = sample_data(df_plot)
    
    hue_col = bin_var.get() if bin_var.get() in df_plot.columns else None

    sns.scatterplot(data=df_plot, x=x_col, y=y_col, hue=hue_col, ax=ax, alpha=0.7)

    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(f"{y_col} от {x_col} (точек: {len(df_plot)})")
    if hue_col:
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

    fig.tight_layout()
    canvas.draw_idle()


def plot_heat_map():
    global current_chart
    current_chart = "heatmap"
    clear_figure()
    ax = fig.add_subplot(111)

    df_plot = get_plot_data()
    
    index_col = hm_index_var.get()
    columns_col = hm_col_var.get()
    values_col = 'cal'
    
    # Проверка наличия колонок
    for col in [index_col, columns_col, values_col]:
        if col not in df_plot.columns:
            ax.set_title(f"Колонка '{col}' не найдена")
            fig.tight_layout()
            canvas.draw_idle()
            return
    
    try:
        # 🔧 КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: бинним числовые колонки для pivot
        df_hm = df_plot.copy()
        
        # Функция для биннинга числовых колонок
        def make_categorical(df, col, n_bins=4):
            if df[col].dtype in ['float64', 'int64'] and df[col].nunique() > n_bins:
                try:
                    return pd.qcut(df[col], q=n_bins, labels=False, duplicates='drop')
                except:
                    return pd.cut(df[col], bins=n_bins, labels=False, duplicates='drop')
            return df[col]
        
        # Применяем биннинг к осям, если они числовые
        idx_data = make_categorical(df_hm, index_col)
        col_data = make_categorical(df_hm, columns_col)
        
        # Создаём временные колонки для pivot
        df_hm['_hm_index'] = idx_data
        df_hm['_hm_columns'] = col_data
        
        # Строим сводную таблицу
        pivot_data = df_hm.pivot_table(
            values=values_col, 
            index='_hm_index', 
            columns='_hm_columns', 
            aggfunc=agg_var.get()
        )
        
        if pivot_data.empty or pivot_data.isna().all().all():
            ax.set_title("⚠️ Нет данных для отображения")
            fig.tight_layout()
            canvas.draw_idle()
            return
        
        # Рисуем heatmap
        sns.heatmap(pivot_data, annot=True, fmt='.0f', cmap='YlOrRd', 
                   cbar_kws={'label': values_col}, ax=ax)
        
        # Подписи с оригинальными названиями колонок
        ax.set_xlabel(f"{columns_col} (группы)")
        ax.set_ylabel(f"{index_col} (группы)")
        ax.set_title(f"{values_col}: {agg_var.get()} по {index_col} × {columns_col}")
        
    except Exception as e:
        ax.set_title(f"Ошибка heatmap")
        print(f"Heatmap Error: {e}")
        import traceback
        traceback.print_exc()
    
    fig.tight_layout()
    canvas.draw_idle()


def refresh_data():
    global df_work, df_filtered
    df_work = preprocess_data()
    df_filtered = df_work.copy()
    apply_filters()

def export_plot():
    filepath = filedialog.asksaveasfilename(defaultextension=".png",
    filetypes=[("PNG", "*.png"), ("PDF", "*.pdf")])
    if filepath:
      fig.savefig(filepath, dpi=300, bbox_inches='tight')    


tk.Button(ctrl_frame, text="Линейный", command=lambda: [plot_line()], width=14).pack(side=tk.LEFT, padx=4)
tk.Button(ctrl_frame, text="Столбчатый", command=lambda: [plot_bar()], width=14).pack(side=tk.LEFT,padx=4)
tk.Button(ctrl_frame, text="Точечный", command=lambda: [plot_scatter()], width=14).pack(side=tk.LEFT,padx=4)
tk.Button(ctrl_frame, text="Тепловая карта", command=lambda: [plot_heat_map()], width=14).pack(side=tk.LEFT,padx=4)

tk.Button(ctrl_frame, text=" Обновить", command=refresh_data, width=12).pack(side=tk.RIGHT,padx=4)
tk.Button(ctrl_frame, text=" Экспорт", command=export_plot, width=12).pack(side=tk.RIGHT,padx=4)      


df_work = preprocess_data()
df_filtered = df_work.copy()
plot_line()

root.mainloop()