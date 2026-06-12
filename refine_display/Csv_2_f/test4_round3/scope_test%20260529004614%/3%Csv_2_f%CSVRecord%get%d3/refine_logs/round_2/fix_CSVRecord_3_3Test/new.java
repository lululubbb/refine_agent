package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

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

        String result = invokeGetMethod(record, "header1");
        Assertions.assertEquals("value1", result);
    }

    @Test
    public void testGet_headerNotMapped() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        
        String[] values = {"value1"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        String result = invokeGetMethod(record, "header2");
        Assertions.assertNull(result);
    }

    @Test
    public void testGet_noHeaderMapping() throws Exception {
        String[] values = {"value1"};
        CSVRecord record = new CSVRecord(values, null, null, 1);

        IllegalStateException exception = Assertions.assertThrows(IllegalStateException.class, () -> {
            invokeGetMethod(record, "header1");
        });
        Assertions.assertEquals("No header mapping was specified, the record values can't be accessed by name", exception.getCause().getMessage());
    }

    @Test
    public void testGet_indexOutOfBounds() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 2); // Set to an out-of-bounds index
        
        String[] values = {"value1", "value2"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        IllegalArgumentException exception = Assertions.assertThrows(IllegalArgumentException.class, () -> {
            invokeGetMethod(record, "header1");
        });
        Assertions.assertEquals("Index for header 'header1' is 2 but CSVRecord only has 2 values!", exception.getCause().getMessage());
    }

    private String invokeGetMethod(CSVRecord record, String header) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("get", String.class);
        method.setAccessible(true);
        return (String) method.invoke(record, header);
    }
}