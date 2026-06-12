package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_3_4Test {

    @Test
    public void testGet_normalCase() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        mapping.put("age", 1);
        String[] values = {"John", "30"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        String result = invokeGetMethod(record, "name");
        Assertions.assertEquals("John", result);

        result = invokeGetMethod(record, "age");
        Assertions.assertEquals("30", result);
    }

    @Test
    public void testGet_nonExistentKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        String[] values = {"John"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        String result = invokeGetMethod(record, "age");
        Assertions.assertNull(result);
    }

    @Test
    public void testGet_noMapping() throws Exception {
        String[] values = {"John", "30"};
        CSVRecord record = new CSVRecord(values, null, null, 1);

        Assertions.assertThrows(IllegalStateException.class, () -> {
            invokeGetMethod(record, "name");
        });
    }

    @Test
    public void testGet_indexOutOfBounds() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        String[] values = {"John"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        Assertions.assertThrows(IllegalArgumentException.class, () -> {
            invokeGetMethod(record, "age");
        });
    }

    private String invokeGetMethod(CSVRecord record, String name) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("get", String.class);
        method.setAccessible(true);
        return (String) method.invoke(record, name);
    }
}