import tkinter as tk
from tkinter import messagebox

class CriblLoadBalancerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Cribl Load Balancer")
        self.worker_nodes = []
        self.total_weight = 0
        self.create_widgets()

    def add_worker_node(self, weight):
        if weight <= 0:
            raise ValueError("Weight must be a positive number.")
        self.worker_nodes.append(weight)
        self.total_weight += weight

    def distribute_load(self):
        distribution = []
        for weight in self.worker_nodes:
            load_percentage = (weight / self.total_weight) * 100
            distribution.append(load_percentage)
        return distribution

    def display_distribution(self):
        distribution = self.distribute_load()
        result_text = "\n".join([f"Worker Node {i+1}: {load:.2f}%" for i, load in enumerate(distribution)])
        messagebox.showinfo("Load Distribution", result_text)

    def submit(self):
        try:
            num_nodes = int(self.nodes_entry.get())
            self.worker_nodes.clear()
            self.total_weight = 0
            for i in range(num_nodes):
                weight = float(self.weights_entries[i].get())
                self.add_worker_node(weight)
            self.display_distribution()
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def create_widgets(self):
        tk.Label(self.root, text="Number of worker nodes:").pack()
        self.nodes_entry = tk.Entry(self.root)
        self.nodes_entry.pack()
        tk.Button(self.root, text="Set Nodes", command=self.set_nodes).pack()
        self.weights_frame = tk.Frame(self.root)
        self.weights_frame.pack()
        tk.Button(self.root, text="Calculate Distribution", command=self.submit).pack()

    def set_nodes(self):
        try:
            num_nodes = int(self.nodes_entry.get())
            for widget in self.weights_frame.winfo_children():
                widget.destroy()
            self.weights_entries = []
            for i in range(num_nodes):
                tk.Label(self.weights_frame, text=f"Weight for node {i+1}:").pack()
                weight_entry = tk.Entry(self.weights_frame)
                weight_entry.pack()
                self.weights_entries.append(weight_entry)
        except ValueError as e:
            messagebox.showerror("Error", str(e))

def main():
    root = tk.Tk()
    app = CriblLoadBalancerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
