package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_3_2Test {

    @Test
    public void testGet_normalCase() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        String[] values = {"John Doe"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = invokeGet(record, "name");
        
        Assertions.assertEquals("John Doe", result);
    }

    @Test
    public void testGet_nonExistentHeader() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        String[] values = {"John Doe"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = invokeGet(record, "age");
        
        Assertions.assertNull(result);
    }

    @Test
    public void testGet_nullMapping() throws Exception {
        String[] values = {"John Doe"};
        CSVRecord record = new CSVRecord(values, null, null, 1);
        
        Assertions.assertThrows(IllegalStateException.class, () -> {
            invokeGet(record, "name");
        });
    }

    @Test
    public void testGet_indexOutOfBounds() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 1);
        String[] values = {"John Doe"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertThrows(IllegalArgumentException.class, () -> {
            invokeGet(record, "name");
        });
    }

    private String invokeGet(CSVRecord record, String name) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("get", String.class);
        method.setAccessible(true);
        return (String) method.invoke(record, name);
    }
}