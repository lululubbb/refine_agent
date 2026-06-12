package org.apache.commons.csv;

import java.util.Arrays;
import java.util.Iterator;
import java.io.Serializable;
import java.lang.reflect.Method;
import java.lang.reflect.InvocationTargetException;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class CSVRecord_3_4Test {
    private CSVRecord csvRecord;
    private Map<String, Integer> mapping;

    @BeforeEach
    public void setUp() {
        String[] values = {"value1", "value2", "value3"};
        mapping = new HashMap<>();
        mapping.put("header1", 0);
        mapping.put("header2", 1);
        mapping.put("header3", 2);
        csvRecord = new CSVRecord(values, mapping, null, 1);
    }

    @Test
    public void testGet_normalCase() throws Exception {
        String result = invokeGetMethod("header1");
        Assertions.assertEquals("value1", result);
    }

    @Test
    public void testGet_nonExistentHeader() throws Exception {
        String result = invokeGetMethod("header4");
        Assertions.assertNull(result);
    }

    @Test
    public void testGet_nullMapping() throws Exception {
        CSVRecord recordWithNullMapping = new CSVRecord(new String[]{"value1"}, null, null, 1);
        IllegalStateException thrown = Assertions.assertThrows(IllegalStateException.class, () -> {
            recordWithNullMapping.get("header1");
        });
        Assertions.assertEquals("No header mapping was specified, the record values can't be accessed by name", thrown.getMessage());
    }

    @Test
    public void testGet_indexOutOfBounds() throws Exception {
        mapping.put("header2", 5); // intentionally setting an out-of-bounds index
        IllegalArgumentException thrown = Assertions.assertThrows(IllegalArgumentException.class, () -> {
            invokeGetMethod("header2");
        });
        Assertions.assertEquals("Index for header 'header2' is 5 but CSVRecord only has 3 values!", thrown.getMessage());
    }

    private String invokeGetMethod(String header) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("get", String.class);
        method.setAccessible(true);
        try {
            return (String) method.invoke(csvRecord, header);
        } catch (InvocationTargetException e) {
            throw e.getCause(); // unwrap the InvocationTargetException to throw the actual cause
        }
    }
}