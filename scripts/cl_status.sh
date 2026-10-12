echo "--- node"; tail -n 6 /tmp/cl_node.log | cut -c1-220
echo "--- gz"; tail -n 2 /tmp/gz.log 2>/dev/null | cut -c1-200
echo "--- bridge"; tail -n 2 /tmp/br.log 2>/dev/null | cut -c1-200
