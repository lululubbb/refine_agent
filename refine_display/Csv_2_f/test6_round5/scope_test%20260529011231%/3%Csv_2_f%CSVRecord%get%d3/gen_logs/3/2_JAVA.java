package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_3_3Test {

    @Test
    public void testGet_normalCase() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        mapping.put("header2", 1);
        String[] values = {"value1", "value2"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        String result = invokeGet(record, "header1");
        Assertions.assertEquals("value1", result);

        result = invokeGet(record, "header2");
        Assertions.assertEquals("value2", result);
    }

    @Test
    public void testGet_nullMapping() {
        String[] values = {"value1", "value2"};
        CSVRecord record = new CSVRecord(values, null, null, 1);

        Assertions.assertThrows(IllegalStateException.class, () -> {
            invokeGet(record, "header1");
        });
    }

    @Test
    public void testGet_indexNotFound() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        String[] values = {"value1"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        String result = invokeGet(record, "header2");
        Assertions.assertNull(result);
    }

    @Test
    public void testGet_indexOutOfBounds() {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 1);
        String[] values = {"value1"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        Assertions.assertThrows(IllegalArgumentException.class, () -> {
            invokeGet(record, "header1");
        });
    }

    private String invokeGet(CSVRecord record, String name) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("get", String.class);
        method.setAccessible(true);
        return (String) method.invoke(record, name);
    }
}