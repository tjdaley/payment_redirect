import psutil
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64

def fig_to_base64(fig):
    image = io.BytesIO()
    fig.savefig(image, format='png', bbox_inches='tight')
    image.seek(0)
    return base64.b64encode(image.getvalue())


print("Gathering CPU Utilization Information")
cpu_utlization = []
for x in range(5):
    cpu_utlization.append(psutil.cpu_percent(interval=1, percpu=True))

matrix = np.array(cpu_utlization)
by_cpu = np.rot90(matrix)

print("Generating graphs")
idx = 0
figs = []
for cpu in by_cpu:
    s = pd.Series(cpu)
    fig, ax = plt.subplots()
    s.plot.bar(color='green', ylim=(0,100))
    fig.savefig(f'cpu_{idx}.png')
    figs.append(fig_to_base64(fig))
    idx += 1

with open('test.html', 'w') as html:
    html.write('<html><body>')
    for fig in figs:
        html.write('<img height="10%" src="data:image/png;base64, {}">'.format(fig.decode('utf-8')))
    html.write('</body></html>')
