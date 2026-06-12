package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_2_2Test {
    private CSVRecord csvRecord;

    @BeforeEach
    public void setUp() {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2);
        csvRecord = new CSVRecord(values, mapping, null, 1);
    }

    @Test
    public void testGet_validIndex() throws Exception {
        String result = invokeGetMethod(1);
        Assertions.assertEquals("value2", result);
    }

    @Test
    public void testGet_firstIndex() throws Exception {
        String result = invokeGetMethod(0);
        Assertions.assertEquals("value1", result);
    }

    @Test
    public void testGet_lastIndex() throws Exception {
        String result = invokeGetMethod(2);
        Assertions.assertEquals("value3", result);
    }

    @Test
    public void testGet_invalidIndex() throws Exception {
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            invokeGetMethod(3);
        });
    }

    private String invokeGetMethod(int index) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("get", int.class);
        method.setAccessible(true);
        return (String) method.invoke(csvRecord, index);
    }
}