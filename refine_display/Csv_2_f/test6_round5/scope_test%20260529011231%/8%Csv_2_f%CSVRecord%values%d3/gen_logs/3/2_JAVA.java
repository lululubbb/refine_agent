package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_8_3Test {

    @Test
    public void testvalues_normalCase() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1);

        String[] result = invokeValues(csvRecord);
        Assertions.assertArrayEquals(values, result);
    }

    @Test
    public void testvalues_emptyArray() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1);

        String[] result = invokeValues(csvRecord);
        Assertions.assertArrayEquals(values, result);
    }

    @Test
    public void testvalues_singleElement() throws Exception {
        String[] values = {"singleValue"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1);

        String[] result = invokeValues(csvRecord);
        Assertions.assertArrayEquals(values, result);
    }

    @Test
    public void testvalues_nullValues() throws Exception {
        String[] values = null;
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1);

        String[] result = invokeValues(csvRecord);
        Assertions.assertNull(result);
    }

    private String[] invokeValues(CSVRecord csvRecord) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("values");
        method.setAccessible(true);
        return (String[]) method.invoke(csvRecord);
    }
}