package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_2_5Test {

    @Test
    public void testGet_validIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = invokeGet(record, 1);
        
        Assertions.assertEquals("value2", result);
    }

    @Test
    public void testGet_boundaryIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = invokeGet(record, 0);
        
        Assertions.assertEquals("value1", result);
    }

    @Test
    public void testGet_invalidIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Exception exception = Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            invokeGet(record, 3);
        });
        
        Assertions.assertEquals("Index 3 out of bounds for length 3", exception.getMessage());
    }

    @Test
    public void testGet_emptyArray() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Exception exception = Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            invokeGet(record, 0);
        });
        
        Assertions.assertEquals("Index 0 out of bounds for length 0", exception.getMessage());
    }

    @Test
    public void testGet_negativeIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Exception exception = Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            invokeGet(record, -1);
        });
        
        Assertions.assertEquals("Index -1 out of bounds for length 3", exception.getMessage());
    }

    @Test
    public void testGet_maxIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = invokeGet(record, 2);
        
        Assertions.assertEquals("value3", result);
    }

    private String invokeGet(CSVRecord record, int index) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("get", int.class);
        method.setAccessible(true);
        return (String) method.invoke(record, index);
    }
}